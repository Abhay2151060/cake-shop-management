from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User, AuditLog
from utils.auth_helper import require_owner, get_shop_settings
from utils.templating import templates

router = APIRouter(prefix="/audit-logs", tags=["audit"])

@router.get("", response_class=HTMLResponse)
def audit_logs_page(
    request: Request,
    module: str = "",
    search: str = "",
    user: User = Depends(require_owner),
    db: Session = Depends(get_db)
):
    settings = get_shop_settings(db)
    query = db.query(AuditLog).order_by(AuditLog.created_at.desc())

    if module.strip():
        query = query.filter(AuditLog.module == module.strip())

    if search.strip():
        s = f"%{search.strip()}%"
        query = query.filter(
            (AuditLog.action.like(s)) |
            (AuditLog.user_name.like(s)) |
            (AuditLog.details.like(s)) |
            (AuditLog.record_id.like(s))
        )

    logs = query.limit(150).all()

    # Get list of unique modules for filter dropdown
    modules_list = [row[0] for row in db.query(AuditLog.module).distinct().all()]

    return templates.TemplateResponse(request=request, name="audit/list.html", context={
        "request": request,
        "user": user,
        "settings": settings,
        "logs": logs,
        "modules_list": modules_list,
        "selected_module": module,
        "search": search
    })
