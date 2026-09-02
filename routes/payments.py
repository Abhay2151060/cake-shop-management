from fastapi import APIRouter, Request, Depends, Body
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User, Order, Payment
from utils.auth_helper import require_login, get_shop_settings
from utils.audit_helper import log_activity
from utils.templating import templates

router = APIRouter(prefix="/payments", tags=["payments"])

MAX_PENDING_ROWS = 500
ALLOWED_PAYMENT_METHODS = ("cash", "upi")


@router.get("/pending", response_class=HTMLResponse)
def pending_payments_page(
    request: Request,
    search: str = "",
    user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    settings = get_shop_settings(db)
    query = db.query(Order).filter(
        Order.payment_status.in_(["pending", "partially_paid"]),
        Order.order_status != "cancelled"
    )

    if search.strip():
        s = f"%{search.strip()}%"
        query = query.filter(
            (Order.order_number.like(s)) |
            (Order.customer_name.like(s)) |
            (Order.customer_phone.like(s))
        )

    # The KPI totals must reflect every pending order, not just the rows shown,
    # so they are aggregated in SQL rather than over a truncated Python list.
    from sqlalchemy import func
    totals = db.query(
        func.coalesce(func.sum(Order.pending_amount), 0.0),
        func.count(Order.id)
    ).filter(
        Order.payment_status.in_(["pending", "partially_paid"]),
        Order.order_status != "cancelled"
    ).one()
    total_pending_amount, total_pending_orders = totals

    status_counts = dict(
        db.query(Order.payment_status, func.count(Order.id)).filter(
            Order.payment_status.in_(["pending", "partially_paid"]),
            Order.order_status != "cancelled"
        ).group_by(Order.payment_status).all()
    )

    pending_orders = query.order_by(Order.created_at.desc()).limit(MAX_PENDING_ROWS).all()

    return templates.TemplateResponse(request=request, name="payments/pending.html", context={
        "user": user,
        "settings": settings,
        "orders": pending_orders,
        "search": search,
        "total_pending_amount": round(float(total_pending_amount or 0.0), 2),
        "total_pending_orders": total_pending_orders,
        "fully_pending_count": status_counts.get("pending", 0),
        "partial_count": status_counts.get("partially_paid", 0),
        "row_limit": MAX_PENDING_ROWS
    })


@router.post("/api/record")
def record_payment_api(
    request: Request,
    payload: dict = Body(...),
    user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    if not isinstance(payload, dict):
        return JSONResponse({"success": False, "error": "Malformed request body."}, status_code=400)

    try:
        order_id = int(payload.get("order_id"))
    except (TypeError, ValueError):
        return JSONResponse({"success": False, "error": "A valid order must be selected."}, status_code=400)

    try:
        amount = round(float(payload.get("amount", 0.0)), 2)
    except (TypeError, ValueError):
        return JSONResponse({"success": False, "error": "Payment amount must be a number."}, status_code=400)

    if amount != amount or amount in (float("inf"), float("-inf")):
        return JSONResponse({"success": False, "error": "Payment amount must be a finite number."}, status_code=400)
    if amount <= 0:
        return JSONResponse({"success": False, "error": "Payment amount must be greater than zero."}, status_code=400)

    payment_method = payload.get("payment_method", "cash")
    if payment_method not in ALLOWED_PAYMENT_METHODS:
        return JSONResponse({"success": False, "error": "Unsupported payment method."}, status_code=400)

    raw_notes = payload.get("notes")
    if raw_notes is not None and not isinstance(raw_notes, str):
        return JSONResponse({"success": False, "error": "Notes must be text."}, status_code=400)
    notes = (raw_notes or "").strip()[:500] or None

    # Lock the row for the read-modify-write so two concurrent collections
    # cannot both pass the balance check and overpay the order.
    order = db.query(Order).filter(Order.id == order_id).with_for_update().first()
    if not order:
        return JSONResponse({"success": False, "error": "Order not found."}, status_code=404)

    if order.order_status == "cancelled":
        return JSONResponse({"success": False, "error": "Cannot record a payment against a cancelled order."}, status_code=409)

    if order.pending_amount <= 0:
        return JSONResponse({"success": False, "error": "This order has no outstanding balance."}, status_code=409)

    if amount > order.pending_amount:
        return JSONResponse({
            "success": False,
            "error": f"Payment amount (₹{amount:,.2f}) cannot exceed current pending balance (₹{order.pending_amount:,.2f})."
        }, status_code=400)

    db.add(Payment(
        order_id=order.id,
        user_id=user.id,
        amount=amount,
        payment_method=payment_method,
        notes=notes or f"Pending balance settlement by {user.name}"
    ))

    order.paid_amount = round(order.paid_amount + amount, 2)
    order.pending_amount = max(0.0, round(order.grand_total - order.paid_amount, 2))
    order.payment_status = "paid" if order.pending_amount == 0.0 else "partially_paid"

    db.commit()

    log_activity(
        db,
        action="Payment Recorded",
        module="Payments",
        record_id=order.order_number,
        details=f"Received payment of ₹{amount} ({payment_method.upper()}) for order {order.order_number}. Remaining pending: ₹{order.pending_amount}",
        user=user,
        request=request
    )

    return JSONResponse({
        "success": True,
        "message": "Payment recorded successfully!",
        "new_paid_amount": order.paid_amount,
        "new_pending_amount": order.pending_amount,
        "new_payment_status": order.payment_status
    })
