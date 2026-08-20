from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models import User, InventoryItem, InventoryTransaction
from utils.auth_helper import require_owner, require_login, get_shop_settings
from utils.audit_helper import log_activity

router = APIRouter(prefix="/inventory", tags=["inventory"])
templates = Jinja2Templates(directory="templates")

@router.get("", response_class=HTMLResponse)
def inventory_list_page(
    request: Request,
    type_filter: str = "",
    search: str = "",
    tab: str = "items",
    user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    settings = get_shop_settings(db)
    query = db.query(InventoryItem).order_by(InventoryItem.name.asc())

    if type_filter.strip():
        query = query.filter(InventoryItem.item_type == type_filter.strip())

    if search.strip():
        s = f"%{search.strip()}%"
        query = query.filter(
            (InventoryItem.name.like(s)) |
            (InventoryItem.supplier.like(s))
        )

    items = query.all()
    low_stock_items = [i for i in items if i.is_low_stock]

    # Fetch recent transactions
    transactions = db.query(InventoryTransaction).order_by(InventoryTransaction.created_at.desc()).limit(50).all()

    return templates.TemplateResponse(request=request, name="inventory/list.html", context={
        "request": request,
        "user": user,
        "settings": settings,
        "items": items,
        "low_stock_items": low_stock_items,
        "transactions": transactions,
        "type_filter": type_filter,
        "search": search,
        "tab": tab,
        "message": request.query_params.get("message"),
        "error": request.query_params.get("error")
    })

@router.post("/create")
def inventory_create(
    request: Request,
    name: str = Form(...),
    item_type: str = Form("raw_material"),
    unit: str = Form("KG"),
    current_qty: float = Form(0.0),
    min_qty: float = Form(5.0),
    purchase_price: float = Form(0.0),
    supplier: str = Form(None),
    expiry_date: str = Form(None),
    user: User = Depends(require_owner),
    db: Session = Depends(get_db)
):
    name_clean = name.strip()
    if not name_clean:
        return RedirectResponse(url="/inventory?error=Item+name+is+required", status_code=status.HTTP_302_FOUND)

    existing = db.query(InventoryItem).filter(InventoryItem.name == name_clean).first()
    if existing:
        return RedirectResponse(url="/inventory?error=An+inventory+item+with+this+name+already+exists", status_code=status.HTTP_302_FOUND)

    c_qty = max(0.0, float(current_qty))
    new_item = InventoryItem(
        name=name_clean,
        item_type=item_type,
        unit=unit.strip(),
        current_qty=c_qty,
        min_qty=max(0.0, float(min_qty)),
        purchase_price=max(0.0, float(purchase_price)),
        supplier=supplier.strip() if supplier else None,
        expiry_date=expiry_date.strip() if expiry_date else None,
        status="active"
    )
    db.add(new_item)
    db.flush()

    if c_qty > 0:
        db.add(InventoryTransaction(
            inventory_item_id=new_item.id,
            user_id=user.id,
            transaction_type="stock_in",
            quantity=c_qty,
            prev_qty=0.0,
            new_qty=c_qty,
            reason="Initial stock creation"
        ))

    db.commit()

    log_activity(db, action="Inventory Item Created", module="Inventory", record_id=new_item.id, details=f"Added {new_item.name} ({c_qty} {new_item.unit})", user=user, request=request)

    return RedirectResponse(url="/inventory?message=Inventory+item+added+successfully", status_code=status.HTTP_302_FOUND)

@router.post("/{item_id}/update")
def inventory_update(
    item_id: int,
    request: Request,
    name: str = Form(...),
    item_type: str = Form("raw_material"),
    unit: str = Form("KG"),
    min_qty: float = Form(5.0),
    purchase_price: float = Form(0.0),
    supplier: str = Form(None),
    expiry_date: str = Form(None),
    status: str = Form("active"),
    user: User = Depends(require_owner),
    db: Session = Depends(get_db)
):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        return RedirectResponse(url="/inventory?error=Item+not+found", status_code=status.HTTP_302_FOUND)

    name_clean = name.strip()
    if name_clean != item.name:
        existing = db.query(InventoryItem).filter(InventoryItem.name == name_clean, InventoryItem.id != item_id).first()
        if existing:
            return RedirectResponse(url="/inventory?error=Another+item+already+has+this+name", status_code=status.HTTP_302_FOUND)

    item.name = name_clean
    item.item_type = item_type
    item.unit = unit.strip()
    item.min_qty = max(0.0, float(min_qty))
    item.purchase_price = max(0.0, float(purchase_price))
    item.supplier = supplier.strip() if supplier else None
    item.expiry_date = expiry_date.strip() if expiry_date else None
    item.status = status

    db.commit()

    log_activity(db, action="Inventory Item Updated", module="Inventory", record_id=item.id, details=f"Updated details for {item.name}", user=user, request=request)

    return RedirectResponse(url="/inventory?message=Inventory+item+updated+successfully", status_code=status.HTTP_302_FOUND)

@router.post("/{item_id}/stock-action")
def inventory_stock_action(
    item_id: int,
    request: Request,
    action_type: str = Form(...),  # 'stock_in', 'stock_out', 'adjustment'
    quantity: float = Form(...),
    reason: str = Form(None),
    user: User = Depends(require_owner),
    db: Session = Depends(get_db)
):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        return RedirectResponse(url="/inventory?error=Item+not+found", status_code=status.HTTP_302_FOUND)

    qty_val = float(quantity)
    if qty_val <= 0 and action_type != "adjustment":
        return RedirectResponse(url="/inventory?error=Quantity+must+be+greater+than+zero", status_code=status.HTTP_302_FOUND)

    prev_qty = item.current_qty

    if action_type == "stock_in":
        new_qty = round(prev_qty + qty_val, 2)
    elif action_type == "stock_out":
        if qty_val > prev_qty:
            return RedirectResponse(url="/inventory?error=Cannot+reduce+more+stock+than+currently+available", status_code=status.HTTP_302_FOUND)
        new_qty = round(prev_qty - qty_val, 2)
    elif action_type == "adjustment":
        new_qty = max(0.0, round(qty_val, 2))
    else:
        return RedirectResponse(url="/inventory?error=Invalid+stock+action", status_code=status.HTTP_302_FOUND)

    item.current_qty = new_qty

    # Record movement transaction
    tx = InventoryTransaction(
        inventory_item_id=item.id,
        user_id=user.id,
        transaction_type=action_type,
        quantity=qty_val,
        prev_qty=prev_qty,
        new_qty=new_qty,
        reason=reason.strip() if reason else f"{action_type.replace('_', ' ').title()} by {user.name}"
    )
    db.add(tx)
    db.commit()

    log_activity(
        db,
        action=f"Inventory {action_type.title()}",
        module="Inventory",
        record_id=item.id,
        details=f"{action_type.replace('_', ' ').title()} on {item.name}: changed from {prev_qty} to {new_qty} {item.unit}",
        user=user,
        request=request
    )

    return RedirectResponse(url=f"/inventory?message=Stock+{action_type.replace('_', '+')}+recorded+successfully&tab=transactions", status_code=status.HTTP_302_FOUND)

@router.post("/{item_id}/delete")
def inventory_delete(
    item_id: int,
    request: Request,
    user: User = Depends(require_owner),
    db: Session = Depends(get_db)
):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        return RedirectResponse(url="/inventory?error=Item+not+found", status_code=status.HTTP_302_FOUND)

    name = item.name
    db.delete(item)
    db.commit()

    log_activity(db, action="Inventory Item Deleted", module="Inventory", record_id=item_id, details=f"Deleted inventory item {name}", user=user, request=request)

    return RedirectResponse(url="/inventory?message=Inventory+item+deleted+successfully", status_code=status.HTTP_302_FOUND)
