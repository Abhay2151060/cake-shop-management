import os
import shutil
import datetime
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status, UploadFile, File, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models import User, CustomCakeOrder
from utils.auth_helper import require_login, get_shop_settings
from utils.audit_helper import log_activity
from config import CUSTOM_CAKE_UPLOAD_DIR

router = APIRouter(prefix="/custom-cakes", tags=["custom_cakes"])
templates = Jinja2Templates(directory="templates")

def generate_custom_cake_number(db: Session) -> str:
    last_item = db.query(CustomCakeOrder).order_by(CustomCakeOrder.id.desc()).first()
    next_id = (last_item.id + 1) if last_item else 1
    return f"CC-{next_id:06d}"

@router.get("", response_class=HTMLResponse)
def custom_cakes_list_page(
    request: Request,
    status_filter: str = "",
    search: str = "",
    user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    settings = get_shop_settings(db)
    query = db.query(CustomCakeOrder).order_by(CustomCakeOrder.created_at.desc())

    if status_filter.strip():
        query = query.filter(CustomCakeOrder.order_status == status_filter.strip())

    if search.strip():
        s = f"%{search.strip()}%"
        query = query.filter(
            (CustomCakeOrder.custom_order_number.like(s)) |
            (CustomCakeOrder.customer_name.like(s)) |
            (CustomCakeOrder.customer_phone.like(s)) |
            (CustomCakeOrder.flavor.like(s)) |
            (CustomCakeOrder.theme_design.like(s))
        )

    custom_orders = query.all()

    return templates.TemplateResponse(request=request, name="custom_cakes/list.html", context={
        "request": request,
        "user": user,
        "settings": settings,
        "custom_orders": custom_orders,
        "status_filter": status_filter,
        "search": search
    })

@router.get("/create", response_class=HTMLResponse)
def custom_cake_create_page(request: Request, user: User = Depends(require_login), db: Session = Depends(get_db)):
    settings = get_shop_settings(db)
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    return templates.TemplateResponse(request=request, name="custom_cakes/create.html", context={
        "request": request,
        "user": user,
        "settings": settings,
        "today_str": today_str,
        "error": None
    })

@router.post("/create")
async def custom_cake_create_submit(
    request: Request,
    customer_name: str = Form(...),
    customer_phone: str = Form(...),
    flavor: str = Form(...),
    weight: str = Form("1 KG"),
    shape: str = Form("Round"),
    theme_design: str = Form(None),
    cake_message: str = Form(None),
    required_date: str = Form(...),
    required_time: str = Form(None),
    special_instructions: str = Form(None),
    estimated_price: float = Form(0.0),
    advance_paid: float = Form(0.0),
    payment_method: str = Form("cash"),
    reference_image: UploadFile = File(None),
    user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    if not customer_name.strip() or not customer_phone.strip() or not flavor.strip() or not required_date.strip():
        settings = get_shop_settings(db)
        return templates.TemplateResponse(request=request, name="custom_cakes/create.html", context={
            "request": request,
            "user": user,
            "settings": settings,
            "today_str": datetime.date.today().strftime("%Y-%m-%d"),
            "error": "Please fill in all required fields (Name, Phone, Flavor, Required Date)."
        }, status_code=400)

    # Calculate pending amount & payment status
    estimated_price = max(0.0, float(estimated_price))
    advance_paid = max(0.0, float(advance_paid))
    pending_amount = max(0.0, estimated_price - advance_paid)

    if advance_paid >= estimated_price and estimated_price > 0:
        payment_status = "paid"
    elif advance_paid > 0:
        payment_status = "partially_paid"
    else:
        payment_status = "pending"

    # Handle image upload if provided
    image_rel_path = None
    if reference_image and reference_image.filename:
        ext = os.path.splitext(reference_image.filename)[1].lower()
        if ext in [".jpg", ".jpeg", ".png", ".webp"]:
            filename = f"cc_{int(datetime.datetime.now().timestamp())}{ext}"
            file_path = CUSTOM_CAKE_UPLOAD_DIR / filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(reference_image.file, buffer)
            image_rel_path = f"/static/uploads/custom_cakes/{filename}"

    custom_order_number = generate_custom_cake_number(db)

    custom_order = CustomCakeOrder(
        custom_order_number=custom_order_number,
        user_id=user.id,
        customer_name=customer_name.strip(),
        customer_phone=customer_phone.strip(),
        flavor=flavor.strip(),
        weight=weight.strip(),
        shape=shape.strip(),
        theme_design=theme_design.strip() if theme_design else None,
        cake_message=cake_message.strip() if cake_message else None,
        required_date=required_date.strip(),
        required_time=required_time.strip() if required_time else None,
        special_instructions=special_instructions.strip() if special_instructions else None,
        reference_image=image_rel_path,
        estimated_price=estimated_price,
        advance_paid=advance_paid,
        pending_amount=pending_amount,
        payment_status=payment_status,
        payment_method=payment_method,
        order_status="new"
    )

    db.add(custom_order)
    db.commit()

    log_activity(
        db,
        action="Custom Cake Order Created",
        module="Custom Cakes",
        record_id=custom_order_number,
        details=f"Custom cake {custom_order_number} booked for {customer_name}. Flavor: {flavor}, Delivery: {required_date}",
        user=user,
        request=request
    )

    return RedirectResponse(url=f"/custom-cakes/{custom_order.id}?message=Custom+cake+order+created+successfully", status_code=status.HTTP_302_FOUND)

@router.get("/{custom_order_id}", response_class=HTMLResponse)
def custom_cake_details_page(
    custom_order_id: int,
    request: Request,
    user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    settings = get_shop_settings(db)
    order = db.query(CustomCakeOrder).filter(CustomCakeOrder.id == custom_order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Custom cake order not found.")

    return templates.TemplateResponse(request=request, name="custom_cakes/details.html", context={
        "request": request,
        "user": user,
        "settings": settings,
        "order": order,
        "message": request.query_params.get("message")
    })

@router.post("/api/{custom_order_id}/status")
def update_custom_cake_status(
    custom_order_id: int,
    request: Request,
    payload: dict = Body(...),
    user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    order = db.query(CustomCakeOrder).filter(CustomCakeOrder.id == custom_order_id).first()
    if not order:
        return JSONResponse({"success": False, "error": "Custom cake order not found."}, status_code=404)

    new_status = payload.get("status")
    allowed_statuses = ["new", "confirmed", "preparing", "ready", "completed", "cancelled"]
    if new_status not in allowed_statuses:
        return JSONResponse({"success": False, "error": "Invalid status."}, status_code=400)

    old_status = order.order_status
    order.order_status = new_status
    db.commit()

    log_activity(
        db,
        action="Custom Cake Status Updated",
        module="Custom Cakes",
        record_id=order.custom_order_number,
        details=f"Status changed from '{old_status}' to '{new_status}'",
        user=user,
        request=request
    )

    return JSONResponse({"success": True, "new_status": new_status})

@router.post("/api/{custom_order_id}/settle-payment")
def settle_custom_cake_payment(
    custom_order_id: int,
    request: Request,
    payload: dict = Body(...),
    user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    order = db.query(CustomCakeOrder).filter(CustomCakeOrder.id == custom_order_id).first()
    if not order:
        return JSONResponse({"success": False, "error": "Order not found."}, status_code=404)

    amount = float(payload.get("amount", 0.0))
    if amount <= 0:
        return JSONResponse({"success": False, "error": "Amount must be positive."}, status_code=400)

    if amount > order.pending_amount:
        return JSONResponse({"success": False, "error": "Amount exceeds pending balance."}, status_code=400)

    order.advance_paid = round(order.advance_paid + amount, 2)
    order.pending_amount = max(0.0, round(order.estimated_price - order.advance_paid, 2))

    if order.pending_amount == 0.0:
        order.payment_status = "paid"
    else:
        order.payment_status = "partially_paid"

    db.commit()

    log_activity(
        db,
        action="Custom Cake Payment Settled",
        module="Custom Cakes",
        record_id=order.custom_order_number,
        details=f"Settled payment of ₹{amount} for {order.custom_order_number}. Remaining: ₹{order.pending_amount}",
        user=user,
        request=request
    )

    return JSONResponse({
        "success": True,
        "new_advance_paid": order.advance_paid,
        "new_pending_amount": order.pending_amount,
        "new_payment_status": order.payment_status
    })
