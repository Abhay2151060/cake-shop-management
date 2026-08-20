import datetime
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database import get_db
from models import (
    User, Order, OrderItem, Product, Category, Payment,
    InventoryItem, InventoryTransaction
)
from utils.auth_helper import require_login, require_staff, get_shop_settings
from utils.audit_helper import log_activity

router = APIRouter(prefix="/orders", tags=["orders"])
templates = Jinja2Templates(directory="templates")

def generate_order_number(db: Session) -> str:
    last_order = db.query(Order).order_by(Order.id.desc()).first()
    next_id = (last_order.id + 1) if last_order else 1
    return f"ORD-{next_id:06d}"

@router.get("/pos", response_class=HTMLResponse)
def pos_page(request: Request, user: User = Depends(require_login), db: Session = Depends(get_db)):
    settings = get_shop_settings(db)
    categories = db.query(Category).filter(Category.status == "active").all()
    products = db.query(Product).filter(Product.status == "active").order_by(Product.name.asc()).all()

    return templates.TemplateResponse(request=request, name="orders/pos.html", context={
        "request": request,
        "user": user,
        "settings": settings,
        "categories": categories,
        "products": products
    })

@router.post("/api/create")
async def create_order_api(
    request: Request,
    payload: dict = Body(...),
    user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    """
    Creates an order with one or multiple items, discount, payment breakdown, and stock deduction.
    """
    items_data = payload.get("items", [])
    if not items_data:
        return JSONResponse({"success": False, "error": "Order must contain at least one product."}, status_code=400)

    customer_name = payload.get("customer_name", "").strip() or "Walk-in Customer"
    customer_phone = payload.get("customer_phone", "").strip() or None
    discount = float(payload.get("discount", 0.0))
    payment_method = payload.get("payment_method", "cash")  # 'cash', 'upi', 'pending'
    paid_amount = float(payload.get("paid_amount", 0.0))
    notes = payload.get("notes", "").strip() or None
    initial_order_status = payload.get("order_status", "completed")

    # 1. Validate items and calculate subtotal
    subtotal = 0.0
    verified_items = []

    for item in items_data:
        product_id = item.get("product_id")
        quantity = int(item.get("quantity", 1))
        if quantity <= 0:
            return JSONResponse({"success": False, "error": "Quantity must be greater than zero."}, status_code=400)

        product = db.query(Product).filter(Product.id == product_id, Product.status == "active").first()
        if not product:
            return JSONResponse({"success": False, "error": f"Product ID {product_id} not found or inactive."}, status_code=400)

        item_subtotal = round(product.selling_price * quantity, 2)
        subtotal += item_subtotal

        verified_items.append({
            "product": product,
            "quantity": quantity,
            "unit_price": product.selling_price,
            "subtotal": item_subtotal
        })

    subtotal = round(subtotal, 2)
    grand_total = max(0.0, round(subtotal - discount, 2))

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

    # Generate unique order ID
    order_number = generate_order_number(db)

    # 2. Create Order
    new_order = Order(
        order_number=order_number,
        user_id=user.id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        subtotal=subtotal,
        discount=discount,
        grand_total=grand_total,
        paid_amount=paid_amount,
        pending_amount=pending_amount,
        payment_status=payment_status,
        payment_method=payment_method,
        order_status=initial_order_status,
        notes=notes
    )
    db.add(new_order)
    db.flush()

    # 3. Create Order Items & Deduct Stock
    for v_item in verified_items:
        product = v_item["product"]
        qty = v_item["quantity"]

        order_item = OrderItem(
            order_id=new_order.id,
            product_id=product.id,
            product_name=product.name,
            size_weight=product.size_weight,
            unit_price=v_item["unit_price"],
            quantity=qty,
            subtotal=v_item["subtotal"]
        )
        db.add(order_item)

        # Decrement product stock if tracked
        if product.stock_qty is not None:
            product.stock_qty = max(0, product.stock_qty - qty)

    # 4. Record Payment if any amount paid
    if paid_amount > 0:
        db.add(Payment(
            order_id=new_order.id,
            user_id=user.id,
            amount=paid_amount,
            payment_method=payment_method if payment_method in ["cash", "upi"] else "cash",
            notes="Initial POS order payment"
        ))

    db.commit()

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
    user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    settings = get_shop_settings(db)
    query = db.query(Order).order_by(Order.created_at.desc())

    if search.strip():
        search_val = f"%{search.strip()}%"
        query = query.filter(
            (Order.order_number.like(search_val)) |
            (Order.customer_name.like(search_val)) |
            (Order.customer_phone.like(search_val))
        )

    if status_filter.strip():
        query = query.filter(Order.order_status == status_filter.strip())

    if payment_filter.strip():
        query = query.filter(Order.payment_status == payment_filter.strip())

    orders = query.all()

    return templates.TemplateResponse(request=request, name="orders/list.html", context={
        "request": request,
        "user": user,
        "settings": settings,
        "orders": orders,
        "search": search,
        "status_filter": status_filter,
        "payment_filter": payment_filter
    })

@router.get("/current", response_class=HTMLResponse)
def current_orders_page(request: Request, user: User = Depends(require_login), db: Session = Depends(get_db)):
    settings = get_shop_settings(db)
    # Active orders for staff / kitchen queue
    orders = db.query(Order).filter(
        Order.order_status.in_(["new", "confirmed", "preparing", "ready"])
    ).order_by(Order.created_at.asc()).all()

    return templates.TemplateResponse(request=request, name="orders/current.html", context={
        "request": request,
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

    new_status = payload.get("status")
    allowed_statuses = ["new", "confirmed", "preparing", "ready", "completed", "cancelled"]
    if new_status not in allowed_statuses:
        return JSONResponse({"success": False, "error": "Invalid status."}, status_code=400)

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
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    return templates.TemplateResponse(request=request, name="orders/details.html", context={
        "request": request,
        "user": user,
        "settings": settings,
        "order": order
    })

@router.get("/{order_id}/receipt", response_class=HTMLResponse)
def receipt_page(order_id: int, request: Request, user: User = Depends(require_login), db: Session = Depends(get_db)):
    settings = get_shop_settings(db)
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    return templates.TemplateResponse(request=request, name="orders/receipt.html", context={
        "request": request,
        "user": user,
        "settings": settings,
        "order": order
    })
