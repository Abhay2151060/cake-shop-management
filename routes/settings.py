from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User, Setting
from utils.auth_helper import require_owner, get_shop_settings
from utils.audit_helper import log_activity
from utils.templating import templates

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("", response_class=HTMLResponse)
def settings_page(request: Request, user: User = Depends(require_owner), db: Session = Depends(get_db)):
    settings = get_shop_settings(db)
    return templates.TemplateResponse(request=request, name="settings/index.html", context={
        "request": request,
        "user": user,
        "settings": settings,
        "message": request.query_params.get("message"),
        "error": request.query_params.get("error")
    })

@router.post("/update")
def settings_update(
    request: Request,
    shop_name: str = Form(...),
    shop_tagline: str = Form(""),
    shop_address: str = Form(...),
    shop_phone: str = Form(...),
    shop_email: str = Form(...),
    shop_gstin: str = Form(""),
    receipt_footer: str = Form(""),
    currency_symbol: str = Form("₹"),
    theme: str = Form(None),
    user: User = Depends(require_owner),
    db: Session = Depends(get_db)
):
    updates = {
        "shop_name": shop_name.strip(),
        "shop_tagline": shop_tagline.strip(),
        "shop_address": shop_address.strip(),
        "shop_phone": shop_phone.strip(),
        "shop_email": shop_email.strip(),
        "shop_gstin": shop_gstin.strip(),
        "receipt_footer": receipt_footer.strip(),
        "currency_symbol": currency_symbol.strip(),
    }
    if theme:
        updates["theme"] = theme.strip()

    for k, v in updates.items():
        s = db.query(Setting).filter(Setting.key == k).first()
        if s:
            s.value = v
        else:
            db.add(Setting(key=k, value=v))

    db.commit()

    log_activity(db, action="Settings Updated", module="Settings", details="Updated shop information & configuration", user=user, request=request)

    return RedirectResponse(url="/settings?message=Settings+saved+successfully", status_code=status.HTTP_302_FOUND)
