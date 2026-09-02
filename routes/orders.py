from fastapi import APIRouter, Request, Depends, HTTPException, status, Body
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError
from database import get_db
from models import User, Order, OrderItem, Product, Category, Payment
from utils.auth_helper import require_login, get_shop_settings
from utils.audit_helper import log_activity
from utils.templating import templates

router = APIRouter(prefix="/orders", tags=["orders"])

PAGE_SIZE = 50
MAX_ITEMS_PER_ORDER = 100
MAX_QUANTITY_PER_ITEM = 1000

ALLOWED_ORDER_STATUSES = ["new", "confirmed", "preparing", "ready", "completed", "cancelled"]
ALLOWED_PAYMENT_METHODS = ["cash", "upi", "pending"]

# Statuses staff may set. Reversing a completed/cancelled order and cancelling
# an order are owner-level actions (PRD 6: staff may "update allowed order
# statuses" only).
STAFF_ALLOWED_STATUSES = ["new", "confirmed", "preparing", "ready", "completed"]
TERMINAL_STATUSES = ["completed", "cancelled"]


def _as_int(value, field: str, default: int | None = None) -> int:
    """Parse an int from untrusted JSON, raising a 400 rather than a 500."""
    if value is None and default is not None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{field}' must be a whole number.")


def _as_float(value, field: str, default: float = 0.0) -> float:
    """Parse a float from untrusted JSON, raising a 400 rather than a 500."""
    if value is None or value == "":
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{field}' must be a number.")
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        raise ValueError(f"'{field}' must be a finite number.")
    return parsed


def _as_text(value, field: str, max_len: int) -> str | None:
    """Coerce untrusted JSON to a bounded string; None when blank."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"'{field}' must be text.")
    trimmed = value.strip()
    if not trimmed:
        return None
    if len(trimmed) > max_len:
        raise ValueError(f"'{field}' must be at most {max_len} characters.")
    return trimmed


def generate_order_number(db: Session) -> str:
    """
    Build the next human-readable order number.

    Reading max(id) is inherently racy under concurrency, so `order_number` also
    carries a UNIQUE constraint and callers retry on IntegrityError.
    """
    last_order = db.query(Order).order_by(Order.id.desc()).first()
    next_id = (last_order.id + 1) if last_order else 1
    return f"ORD-{next_id:06d}"


@router.get("/pos", response_class=HTMLResponse)
def pos_page(request: Request, user: User = Depends(require_login), db: Session = Depends(get_db)):
    settings = get_shop_settings(db)
    categories = db.query(Category).filter(Category.status == "active").order_by(Category.name.asc()).all()
    products = db.query(Product).filter(Product.status == "active").order_by(Product.name.asc()).all()

    return templates.TemplateResponse(request=request, name="orders/pos.html", context={
        "user": user,
        "settings": settings,
        "categories": categories,
        "products": products
    })


@router.post("/api/create")
def create_order_api(
    request: Request,
    payload: dict = Body(...),
    user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    """
    Creates an order with one or multiple items, payment breakdown and stock
    deduction. All monetary values are recomputed server-side from the product
    catalogue; the client's prices are never trusted.
    """
    if not isinstance(payload, dict):
        return JSONResponse({"success": False, "error": "Malformed request body."}, status_code=400)

    items_data = payload.get("items")
    if not isinstance(items_data, list) or not items_data:
        return JSONResponse({"success": False, "error": "Order must contain at least one product."}, status_code=400)
    if len(items_data) > MAX_ITEMS_PER_ORDER:
        return JSONResponse({"success": False, "error": f"An order cannot contain more than {MAX_ITEMS_PER_ORDER} distinct products."}, status_code=400)

    try:
        customer_name = _as_text(payload.get("customer_name"), "customer_name", 120) or "Walk-in Customer"
        customer_phone = _as_text(payload.get("customer_phone"), "customer_phone", 20)
        notes = _as_text(payload.get("notes"), "notes", 500)
        paid_amount = round(_as_float(payload.get("paid_amount"), "paid_amount", 0.0), 2)

        # Merge duplicate lines for the same product so the stock check below
        # sees the true requested quantity.
        requested: dict[int, int] = {}
        for raw in items_data:
            if not isinstance(raw, dict):
                raise ValueError("Each order item must be an object.")
            product_id = _as_int(raw.get("product_id"), "product_id")
            quantity = _as_int(raw.get("quantity"), "quantity", 1)
            if quantity <= 0:
                raise ValueError("Quantity must be greater than zero.")
            if quantity > MAX_QUANTITY_PER_ITEM:
                raise ValueError(f"Quantity per product cannot exceed {MAX_QUANTITY_PER_ITEM}.")
            requested[product_id] = requested.get(product_id, 0) + quantity
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    if paid_amount < 0:
        return JSONResponse({"success": False, "error": "Paid amount cannot be negative."}, status_code=400)

    payment_method = payload.get("payment_method", "cash")
    if payment_method not in ALLOWED_PAYMENT_METHODS:
        return JSONResponse({"success": False, "error": "Unsupported payment method."}, status_code=400)

    initial_order_status = payload.get("order_status", "completed")
    if initial_order_status not in ALLOWED_ORDER_STATUSES:
        return JSONResponse({"success": False, "error": "Invalid order status."}, status_code=400)

    payment_status_type = payload.get("payment_status_type")

    # 1. Load products and validate availability
    products = db.query(Product).filter(
        Product.id.in_(requested.keys()),
        Product.status == "active"
    ).all()
    products_by_id = {p.id: p for p in products}

    missing = [pid for pid in requested if pid not in products_by_id]
    if missing:
        return JSONResponse(
            {"success": False, "error": f"Product ID {missing[0]} not found or inactive."},
            status_code=400
        )

    subtotal = 0.0
    verified_items = []
    for product_id, quantity in requested.items():
        product = products_by_id[product_id]

        # Prevent overselling: previously stock was clamped with max(0, ...),
        # which silently accepted orders for unavailable stock.
        if product.stock_qty is not None and quantity > product.stock_qty:
            return JSONResponse({
                "success": False,
                "error": f"Insufficient stock for '{product.name}'. Available: {product.stock_qty}, requested: {quantity}."
            }, status_code=409)

        item_subtotal = round(product.selling_price * quantity, 2)
        subtotal += item_subtotal
        verified_items.append({
            "product": product,
            "quantity": quantity,
            "unit_price": product.selling_price,
            "subtotal": item_subtotal
        })

    subtotal = round(subtotal, 2)
    grand_total = subtotal

    if payment_status_type == "partial" and paid_amount <= 0:
        return JSONResponse({"success": False, "error": "For Partial Payment, paid amount must be greater than ₹0.00. Select Udhaar for zero payment."}, status_code=400)

    if paid_amount > grand_total:
        return JSONResponse({"success": False, "error": "Paid amount cannot exceed grand total."}, status_code=400)

    pending_amount = max(0.0, round(grand_total - paid_amount, 2))

    # Determine payment status
    if paid_amount >= grand_total and grand_total > 0:
        payment_status = "paid"
    elif paid_amount == 0:
        payment_status = "pending"
    else:
        payment_status = "partially_paid"

    # 2. Persist, retrying once if a concurrent request claimed the same number.
    for attempt in range(5):
        order_number = generate_order_number(db)
        new_order = Order(
            order_number=order_number,
            user_id=user.id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            subtotal=subtotal,
            discount=0.0,
            grand_total=grand_total,
            paid_amount=paid_amount,
            pending_amount=pending_amount,
            payment_status=payment_status,
            payment_method=payment_method,
            order_status=initial_order_status,
            notes=notes
        )
        db.add(new_order)
        try:
            db.flush()
            break
        except IntegrityError:
            db.rollback()
            if attempt == 4:
                return JSONResponse(
                    {"success": False, "error": "Could not allocate an order number. Please try again."},
                    status_code=409
                )
            # Objects were expired by the rollback; re-fetch the products.
            products = db.query(Product).filter(Product.id.in_(requested.keys())).all()
            products_by_id = {p.id: p for p in products}
            for v_item in verified_items:
                v_item["product"] = products_by_id[v_item["product"].id]

    # 3. Create Order Items & Deduct Stock
    for v_item in verified_items:
        product = v_item["product"]
        qty = v_item["quantity"]

        db.add(OrderItem(
            order_id=new_order.id,
            product_id=product.id,
            product_name=product.name,
            size_weight=product.size_weight,
            unit_price=v_item["unit_price"],
            quantity=qty,
            subtotal=v_item["subtotal"]
        ))

        if product.stock_qty is not None:
            product.stock_qty = max(0, product.stock_qty - qty)

    # 4. Record Payment if any amount paid
    if paid_amount > 0:
        db.add(Payment(
            order_id=new_order.id,
            user_id=user.id,
            amount=paid_amount,
            payment_method=payment_method if payment_method in ("cash", "upi") else "cash",
            notes="Initial POS order payment"
        ))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return JSONResponse({"success": False, "error": "Could not save the order. Please try again."}, status_code=409)

    log_activity(
        db,
        action="Order Created",
        module="Orders",
        record_id=new_order.order_number,
        details=f"Created order {new_order.order_number} for {customer_name}. Total: ₹{grand_total}, Status: {payment_status}",
        user=user,
        request=request
    )

    return JSONResponse({
        "success": True,
        "order_id": new_order.id,
        "order_number": new_order.order_number,
        "receipt_url": f"/orders/{new_order.id}/receipt"
    })


@router.get("", response_class=HTMLResponse)
def orders_list_page(
    request: Request,
    search: str = "",
    status_filter: str = "",
    payment_filter: str = "",
    page: int = 1,
    user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    settings = get_shop_settings(db)
    # selectinload avoids an N+1 COUNT per row for `ord.items|length`.
    query = db.query(Order).options(selectinload(Order.items))

    if search.strip():
        search_val = f"%{search.strip()}%"
        query = query.filter(
            (Order.order_number.like(search_val)) |
            (Order.customer_name.like(search_val)) |
            (Order.customer_phone.like(search_val))
        )

    if status_filter.strip():
        if status_filter.strip() not in ALLOWED_ORDER_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status filter.")
        query = query.filter(Order.order_status == status_filter.strip())

    if payment_filter.strip():
        if payment_filter.strip() not in ("paid", "partially_paid", "pending"):
            raise HTTPException(status_code=400, detail="Invalid payment filter.")
        query = query.filter(Order.payment_status == payment_filter.strip())

    # Paginate: an unbounded .all() would load the entire order history.
    total_orders = query.count()
    total_pages = max(1, (total_orders + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(1, min(page, total_pages))
    orders = (
        query.order_by(Order.created_at.desc(), Order.id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )

    return templates.TemplateResponse(request=request, name="orders/list.html", context={
        "user": user,
        "settings": settings,
        "orders": orders,
        "search": search,
        "status_filter": status_filter,
        "payment_filter": payment_filter,
        "page": page,
        "total_pages": total_pages,
        "total_orders": total_orders
    })


@router.get("/current", response_class=HTMLResponse)
def current_orders_page(request: Request, user: User = Depends(require_login), db: Session = Depends(get_db)):
    settings = get_shop_settings(db)
    # Active orders for staff / kitchen queue
    orders = db.query(Order).options(selectinload(Order.items)).filter(
        Order.order_status.in_(["new", "confirmed", "preparing", "ready"])
    ).order_by(Order.created_at.asc()).limit(200).all()

    return templates.TemplateResponse(request=request, name="orders/current.html", context={
        "user": user,
        "settings": settings,
        "orders": orders
    })


@router.post("/api/{order_id}/status")
def update_order_status(
    order_id: int,
    request: Request,
    payload: dict = Body(...),
    user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return JSONResponse({"success": False, "error": "Order not found."}, status_code=404)

    new_status = payload.get("status") if isinstance(payload, dict) else None
    if new_status not in ALLOWED_ORDER_STATUSES:
        return JSONResponse({"success": False, "error": "Invalid status."}, status_code=400)

    # Staff may progress an order through the kitchen queue, but cancelling or
    # reopening a finalised order is an owner action.
    if user.role != "owner":
        if new_status not in STAFF_ALLOWED_STATUSES:
            return JSONResponse(
                {"success": False, "error": "Only the owner can cancel an order."},
                status_code=403
            )
        if order.order_status in TERMINAL_STATUSES:
            return JSONResponse(
                {"success": False, "error": f"This order is already {order.order_status}. Only the owner can change it."},
                status_code=403
            )

    if order.order_status == new_status:
        return JSONResponse({"success": True, "new_status": new_status})

    old_status = order.order_status
    order.order_status = new_status
    db.commit()

    log_activity(
        db,
        action="Order Status Updated",
        module="Orders",
        record_id=order.order_number,
        details=f"Updated status from '{old_status}' to '{new_status}'",
        user=user,
        request=request
    )

    return JSONResponse({"success": True, "new_status": new_status})


@router.get("/{order_id}", response_class=HTMLResponse)
def order_details_page(order_id: int, request: Request, user: User = Depends(require_login), db: Session = Depends(get_db)):
    settings = get_shop_settings(db)
    order = db.query(Order).options(selectinload(Order.items)).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    return templates.TemplateResponse(request=request, name="orders/details.html", context={
        "user": user,
        "settings": settings,
        "order": order
    })


@router.get("/{order_id}/receipt", response_class=HTMLResponse)
def receipt_page(order_id: int, request: Request, user: User = Depends(require_login), db: Session = Depends(get_db)):
    settings = get_shop_settings(db)
    order = db.query(Order).options(selectinload(Order.items)).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    return templates.TemplateResponse(request=request, name="orders/receipt.html", context={
        "user": user,
        "settings": settings,
        "order": order
    })
