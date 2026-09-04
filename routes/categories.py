from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import User, Category, Product
from utils.auth_helper import require_owner, require_login, get_shop_settings
from utils.audit_helper import log_activity
from utils.templating import templates

router = APIRouter(prefix="/categories", tags=["categories"])

@router.get("", response_class=HTMLResponse)
def categories_list_page(request: Request, user: User = Depends(require_login), db: Session = Depends(get_db)):
    settings = get_shop_settings(db)
    categories = db.query(Category).order_by(Category.name.asc()).all()

    # Map product counts with a single aggregation query
    counts_rows = db.query(Product.category_id, func.count(Product.id)).group_by(Product.category_id).all()
    cat_counts = {cid: cnt for cid, cnt in counts_rows if cid is not None}

    return templates.TemplateResponse(request=request, name="categories/list.html", context={
        "request": request,
        "user": user,
        "settings": settings,
        "categories": categories,
        "cat_counts": cat_counts,
        "message": request.query_params.get("message"),
        "error": request.query_params.get("error")
    })

@router.post("/create")
def category_create(
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    user: User = Depends(require_owner),
    db: Session = Depends(get_db)
):
    name_clean = name.strip()
    if not name_clean:
        return RedirectResponse(url="/categories?error=Category+name+cannot+be+empty", status_code=status.HTTP_302_FOUND)

    existing = db.query(Category).filter(Category.name == name_clean).first()
    if existing:
        return RedirectResponse(url="/categories?error=Category+with+this+name+already+exists", status_code=status.HTTP_302_FOUND)

    new_cat = Category(
        name=name_clean,
        description=description.strip() if description else None,
        status="active"
    )
    db.add(new_cat)
    db.commit()

    log_activity(db, action="Category Created", module="Categories", record_id=new_cat.id, details=f"Created category {new_cat.name}", user=user, request=request)

    return RedirectResponse(url="/categories?message=Category+created+successfully", status_code=status.HTTP_302_FOUND)

@router.post("/{cat_id}/update")
def category_update(
    cat_id: int,
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    cat_status: str = Form("active", alias="status"),
    user: User = Depends(require_owner),
    db: Session = Depends(get_db)
):
    cat = db.query(Category).filter(Category.id == cat_id).first()
    if not cat:
        return RedirectResponse(url="/categories?error=Category+not+found", status_code=status.HTTP_302_FOUND)

    name_clean = name.strip()
    if name_clean != cat.name:
        existing = db.query(Category).filter(Category.name == name_clean, Category.id != cat_id).first()
        if existing:
            return RedirectResponse(url="/categories?error=Another+category+already+has+this+name", status_code=status.HTTP_302_FOUND)

    cat.name = name_clean
    cat.description = description.strip() if description else None
    cat.status = cat_status
    db.commit()

    log_activity(db, action="Category Updated", module="Categories", record_id=cat.id, details=f"Updated category {cat.name}", user=user, request=request)

    return RedirectResponse(url="/categories?message=Category+updated+successfully", status_code=status.HTTP_302_FOUND)

@router.post("/{cat_id}/toggle-status")
def category_toggle_status(
    cat_id: int,
    request: Request,
    user: User = Depends(require_owner),
    db: Session = Depends(get_db)
):
    cat = db.query(Category).filter(Category.id == cat_id).first()
    if not cat:
        return RedirectResponse(url="/categories?error=Category+not+found", status_code=status.HTTP_302_FOUND)

    cat.status = "inactive" if cat.status == "active" else "active"
    db.commit()

    log_activity(db, action="Category Status Toggled", module="Categories", record_id=cat.id, details=f"Set status to {cat.status} for {cat.name}", user=user, request=request)

    return RedirectResponse(url=f"/categories?message=Category+status+changed+to+{cat.status}", status_code=status.HTTP_302_FOUND)

@router.post("/{cat_id}/delete")
def category_delete(
    cat_id: int,
    request: Request,
    user: User = Depends(require_owner),
    db: Session = Depends(get_db)
):
    cat = db.query(Category).filter(Category.id == cat_id).first()
    if not cat:
        return RedirectResponse(url="/categories?error=Category+not+found", status_code=status.HTTP_302_FOUND)

    # Check if products exist in category
    prod_count = db.query(Product).filter(Product.category_id == cat.id).count()
    if prod_count > 0:
        return RedirectResponse(url="/categories?error=Cannot+delete+category+containing+existing+products.+Please+reassign+or+delete+products+first.", status_code=status.HTTP_302_FOUND)

    name = cat.name
    db.delete(cat)
    db.commit()

    log_activity(db, action="Category Deleted", module="Categories", record_id=cat_id, details=f"Deleted category {name}", user=user, request=request)

    return RedirectResponse(url="/categories?message=Category+deleted+successfully", status_code=status.HTTP_302_FOUND)
