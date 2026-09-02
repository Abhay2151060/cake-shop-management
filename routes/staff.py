from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User
from utils.auth_helper import require_owner, get_shop_settings
from utils.audit_helper import log_activity
from utils.templating import templates

router = APIRouter(prefix="/staff", tags=["staff"])

@router.get("", response_class=HTMLResponse)
def staff_list_page(request: Request, user: User = Depends(require_owner), db: Session = Depends(get_db)):
    settings = get_shop_settings(db)
    staff_members = db.query(User).order_by(User.role.asc(), User.name.asc()).all()

    return templates.TemplateResponse(request=request, name="staff/list.html", context={
        "request": request,
        "user": user,
        "settings": settings,
        "staff_members": staff_members,
        "message": request.query_params.get("message"),
        "error": request.query_params.get("error")
    })

@router.post("/create")
def staff_create(
    request: Request,
    name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone: str = Form(None),
    role: str = Form("staff"),
    user: User = Depends(require_owner),
    db: Session = Depends(get_db)
):
    u_clean = username.strip()
    e_clean = email.strip()

    if db.query(User).filter(User.username == u_clean).first():
        return RedirectResponse(url="/staff?error=Username+is+already+taken", status_code=status.HTTP_302_FOUND)

    if db.query(User).filter(User.email == e_clean).first():
        return RedirectResponse(url="/staff?error=Email+is+already+registered", status_code=status.HTTP_302_FOUND)

    new_user = User(
        name=name.strip(),
        username=u_clean,
        email=e_clean,
        phone=phone.strip() if phone else None,
        role=role,
        status="active"
    )
    new_user.set_password(password)
    db.add(new_user)
    db.commit()

    log_activity(db, action="Staff Account Created", module="Staff", record_id=new_user.id, details=f"Created {role} account for {new_user.name} ({new_user.username})", user=user, request=request)

    return RedirectResponse(url="/staff?message=Staff+account+created+successfully", status_code=status.HTTP_302_FOUND)

@router.post("/{user_id}/update")
def staff_update(
    user_id: int,
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    role: str = Form("staff"),
    user: User = Depends(require_owner),
    db: Session = Depends(get_db)
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        return RedirectResponse(url="/staff?error=User+not+found", status_code=status.HTTP_302_FOUND)

    e_clean = email.strip()
    if e_clean != target.email:
        if db.query(User).filter(User.email == e_clean, User.id != user_id).first():
            return RedirectResponse(url="/staff?error=Email+already+in+use", status_code=status.HTTP_302_FOUND)

    target.name = name.strip()
    target.email = e_clean
    target.phone = phone.strip() if phone else None
    target.role = role
    db.commit()

    log_activity(db, action="Staff Account Updated", module="Staff", record_id=target.id, details=f"Updated details for {target.name}", user=user, request=request)

    return RedirectResponse(url="/staff?message=Staff+account+updated+successfully", status_code=status.HTTP_302_FOUND)

@router.post("/{user_id}/reset-password")
def staff_reset_password(
    user_id: int,
    request: Request,
    new_password: str = Form(...),
    user: User = Depends(require_owner),
    db: Session = Depends(get_db)
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        return RedirectResponse(url="/staff?error=User+not+found", status_code=status.HTTP_302_FOUND)

    if len(new_password) < 6:
        return RedirectResponse(url="/staff?error=Password+must+be+at+least+6+characters", status_code=status.HTTP_302_FOUND)

    target.set_password(new_password)
    db.commit()

    log_activity(db, action="Staff Password Reset", module="Staff", record_id=target.id, details=f"Owner reset password for {target.username}", user=user, request=request)

    return RedirectResponse(url="/staff?message=Password+reset+successfully", status_code=status.HTTP_302_FOUND)

@router.post("/{user_id}/toggle-status")
def staff_toggle_status(
    user_id: int,
    request: Request,
    user: User = Depends(require_owner),
    db: Session = Depends(get_db)
):
    if user_id == user.id:
        return RedirectResponse(url="/staff?error=You+cannot+deactivate+your+own+account", status_code=status.HTTP_302_FOUND)

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        return RedirectResponse(url="/staff?error=User+not+found", status_code=status.HTTP_302_FOUND)

    target.status = "inactive" if target.status == "active" else "active"
    db.commit()

    log_activity(db, action="Staff Status Toggled", module="Staff", record_id=target.id, details=f"Changed status to {target.status} for {target.username}", user=user, request=request)

    return RedirectResponse(url=f"/staff?message=Staff+status+changed+to+{target.status}", status_code=status.HTTP_302_FOUND)
