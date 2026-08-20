import datetime
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models import User, Order, Payment
from utils.auth_helper import require_login, get_shop_settings
from utils.audit_helper import log_activity

router = APIRouter(prefix="/payments", tags=["payments"])
templates = Jinja2Templates(directory="templates")

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
    ).order_by(Order.created_at.desc())

    if search.strip():
        s = f"%{search.strip()}%"
        query = query.filter(
            (Order.order_number.like(s)) |
            (Order.customer_name.like(s)) |
            (Order.customer_phone.like(s))
        )

    pending_orders = query.all()

    total_pending_amount = sum(o.pending_amount for o in pending_orders)
    fully_pending_count = sum(1 for o in pending_orders if o.payment_status == "pending")
    partial_count = sum(1 for o in pending_orders if o.payment_status == "partially_paid")

    return templates.TemplateResponse(request=request, name="payments/pending.html", context={
        "request": request,
        "user": user,
        "settings": settings,
        "orders": pending_orders,
        "search": search,
        "total_pending_amount": round(total_pending_amount, 2),
        "fully_pending_count": fully_pending_count,
        "partial_count": partial_count
    })

@router.post("/api/record")
def record_payment_api(
    request: Request,
    payload: dict = Body(...),
    user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    order_id = payload.get("order_id")
    amount = float(payload.get("amount", 0.0))
    payment_method = payload.get("payment_method", "cash")  # 'cash', 'upi'
    notes = payload.get("notes", "").strip() or None

    if amount <= 0:
        return JSONResponse({"success": False, "error": "Payment amount must be greater than zero."}, status_code=400)

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return JSONResponse({"success": False, "error": "Order not found."}, status_code=404)

    if amount > order.pending_amount:
        return JSONResponse({
            "success": False,
            "error": f"Payment amount (₹{amount}) cannot exceed current pending balance (₹{order.pending_amount})."
        }, status_code=400)

    # Record payment transaction
    new_payment = Payment(
        order_id=order.id,
        user_id=user.id,
        amount=amount,
        payment_method=payment_method,
        notes=notes or f"Pending balance settlement by {user.name}"
    )
    db.add(new_payment)

    # Update order totals
    order.paid_amount = round(order.paid_amount + amount, 2)
    order.pending_amount = max(0.0, round(order.grand_total - order.paid_amount, 2))

    if order.pending_amount == 0.0:
        order.payment_status = "paid"
    else:
        order.payment_status = "partially_paid"

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
