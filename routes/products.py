import os
import shutil
import datetime
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models import User, Product, Category, OrderItem
from utils.auth_helper import require_owner, require_login, get_shop_settings
from utils.audit_helper import log_activity
from config import PRODUCT_UPLOAD_DIR

router = APIRouter(prefix="/products", tags=["products"])
templates = Jinja2Templates(directory="templates")

@router.get("", response_class=HTMLResponse)
def products_list_page(
    request: Request,
    category_id: int = 0,
    search: str = "",
    user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    settings = get_shop_settings(db)
    categories = db.query(Category).order_by(Category.name.asc()).all()
    query = db.query(Product).order_by(Product.name.asc())

    if category_id and category_id > 0:
        query = query.filter(Product.category_id == category_id)

    if search.strip():
        s = f"%{search.strip()}%"
        query = query.filter(
            (Product.name.like(s)) |
            (Product.sku.like(s)) |
            (Product.description.like(s))
        )

    products = query.all()

    return templates.TemplateResponse(request=request, name="products/list.html", context={
        "request": request,
        "user": user,
        "settings": settings,
        "products": products,
        "categories": categories,
        "selected_category_id": category_id,
        "search": search,
        "message": request.query_params.get("message"),
        "error": request.query_params.get("error")
    })

@router.post("/create")
async def product_create(
    request: Request,
    name: str = Form(...),
    category_id: int = Form(...),
    sku: str = Form(None),
    description: str = Form(None),
    size_weight: str = Form("1 KG"),
    selling_price: float = Form(0.0),
    cost_price: float = Form(0.0),
    stock_qty: int = Form(0),
    min_stock_level: int = Form(5),
    product_image: UploadFile = File(None),
    user: User = Depends(require_owner),
    db: Session = Depends(get_db)
):
    if not name.strip() or not category_id:
        return RedirectResponse(url="/products?error=Name+and+category+are+required", status_code=status.HTTP_302_FOUND)

    # Check SKU uniqueness if provided
    sku_val = sku.strip() if sku else None
    if sku_val:
        existing = db.query(Product).filter(Product.sku == sku_val).first()
        if existing:
            return RedirectResponse(url="/products?error=SKU+must+be+unique", status_code=status.HTTP_302_FOUND)

    image_rel_path = None
    if product_image and product_image.filename:
        ext = os.path.splitext(product_image.filename)[1].lower()
        if ext in [".jpg", ".jpeg", ".png", ".webp"]:
            filename = f"prod_{int(datetime.datetime.now().timestamp())}{ext}"
            file_path = PRODUCT_UPLOAD_DIR / filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(product_image.file, buffer)
            image_rel_path = f"/static/uploads/products/{filename}"

    new_prod = Product(
        name=name.strip(),
        category_id=category_id,
        sku=sku_val,
        description=description.strip() if description else None,
        size_weight=size_weight.strip(),
        selling_price=max(0.0, float(selling_price)),
        cost_price=max(0.0, float(cost_price)),
        stock_qty=max(0, int(stock_qty)),
        min_stock_level=max(0, int(min_stock_level)),
        image_path=image_rel_path,
        status="active"
    )
    db.add(new_prod)
    db.commit()

    log_activity(db, action="Product Created", module="Products", record_id=new_prod.id, details=f"Created product {new_prod.name} (SKU: {new_prod.sku})", user=user, request=request)

    return RedirectResponse(url="/products?message=Product+created+successfully", status_code=status.HTTP_302_FOUND)

@router.post("/{product_id}/update")
async def product_update(
    product_id: int,
    request: Request,
    name: str = Form(...),
    category_id: int = Form(...),
    sku: str = Form(None),
    description: str = Form(None),
    size_weight: str = Form("1 KG"),
    selling_price: float = Form(0.0),
    cost_price: float = Form(0.0),
    stock_qty: int = Form(0),
    min_stock_level: int = Form(5),
    status: str = Form("active"),
    product_image: UploadFile = File(None),
    user: User = Depends(require_owner),
    db: Session = Depends(get_db)
):
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod:
        return RedirectResponse(url="/products?error=Product+not+found", status_code=status.HTTP_302_FOUND)

    sku_val = sku.strip() if sku else None
    if sku_val and sku_val != prod.sku:
        existing = db.query(Product).filter(Product.sku == sku_val, Product.id != prod.id).first()
        if existing:
            return RedirectResponse(url="/products?error=SKU+must+be+unique", status_code=status.HTTP_302_FOUND)

    if product_image and product_image.filename:
        ext = os.path.splitext(product_image.filename)[1].lower()
        if ext in [".jpg", ".jpeg", ".png", ".webp"]:
            filename = f"prod_{int(datetime.datetime.now().timestamp())}{ext}"
            file_path = PRODUCT_UPLOAD_DIR / filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(product_image.file, buffer)
            prod.image_path = f"/static/uploads/products/{filename}"

    prod.name = name.strip()
    prod.category_id = category_id
    prod.sku = sku_val
    prod.description = description.strip() if description else None
    prod.size_weight = size_weight.strip()
    prod.selling_price = max(0.0, float(selling_price))
    prod.cost_price = max(0.0, float(cost_price))
    prod.stock_qty = max(0, int(stock_qty))
    prod.min_stock_level = max(0, int(min_stock_level))
    prod.status = status

    db.commit()

    log_activity(db, action="Product Updated", module="Products", record_id=prod.id, details=f"Updated product {prod.name}", user=user, request=request)

    return RedirectResponse(url="/products?message=Product+updated+successfully", status_code=status.HTTP_302_FOUND)

@router.post("/{product_id}/toggle-status")
def product_toggle_status(
    product_id: int,
    request: Request,
    user: User = Depends(require_owner),
    db: Session = Depends(get_db)
):
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod:
        return RedirectResponse(url="/products?error=Product+not+found", status_code=status.HTTP_302_FOUND)

    prod.status = "inactive" if prod.status == "active" else "active"
    db.commit()

    log_activity(db, action="Product Status Toggled", module="Products", record_id=prod.id, details=f"Set status to {prod.status} for {prod.name}", user=user, request=request)

    return RedirectResponse(url=f"/products?message=Product+status+changed+to+{prod.status}", status_code=status.HTTP_302_FOUND)

@router.post("/{product_id}/delete")
def product_delete(
    product_id: int,
    request: Request,
    user: User = Depends(require_owner),
    db: Session = Depends(get_db)
):
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod:
        return RedirectResponse(url="/products?error=Product+not+found", status_code=status.HTTP_302_FOUND)

    # Check if used in orders
    order_items_count = db.query(OrderItem).filter(OrderItem.product_id == prod.id).count()
    if order_items_count > 0:
        # Cannot delete without breaking history; deactivate instead
        prod.status = "inactive"
        db.commit()
        log_activity(db, action="Product Deactivated on Delete Attempt", module="Products", record_id=prod.id, details=f"Product {prod.name} has {order_items_count} historical order associations. Deactivated instead.", user=user, request=request)
        return RedirectResponse(url="/products?message=Product+has+existing+orders+and+has+been+deactivated+instead+of+deleted+to+preserve+history", status_code=status.HTTP_302_FOUND)

    name = prod.name
    db.delete(prod)
    db.commit()

    log_activity(db, action="Product Deleted", module="Products", record_id=product_id, details=f"Deleted product {name}", user=user, request=request)

    return RedirectResponse(url="/products?message=Product+deleted+successfully", status_code=status.HTTP_302_FOUND)
