from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models import User
from utils.auth_helper import get_current_user, require_login, get_shop_settings
from utils.audit_helper import log_activity

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="templates")

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    settings = get_shop_settings(db)
    return templates.TemplateResponse(request=request, name="auth/login.html", context={
        "request": request,
        "settings": settings,
        "error": None
    })

@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    settings = get_shop_settings(db)
    user = db.query(User).filter(
        (User.username == username.strip()) | (User.email == username.strip())
    ).first()

    if not user or not user.check_password(password):
        return templates.TemplateResponse(request=request, name="auth/login.html", context={
            "request": request,
            "settings": settings,
            "error": "Invalid username/email or password.",
            "username": username
        }, status_code=400)

    if user.status != "active":
        return templates.TemplateResponse(request=request, name="auth/login.html", context={
            "request": request,
            "settings": settings,
            "error": "Your account has been deactivated. Please contact the owner.",
            "username": username
        }, status_code=403)

    # Store user session
    request.session["user_id"] = user.id
    request.session["user_role"] = user.role
    request.session["user_name"] = user.name

    log_activity(db, action="User Login", module="Auth", record_id=user.id, details=f"User {user.username} logged in successfully.", user=user, request=request)

    return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

@router.get("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        log_activity(db, action="User Logout", module="Auth", record_id=user.id, details=f"User {user.username} logged out.", user=user, request=request)
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

@router.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request, user: User = Depends(require_login), db: Session = Depends(get_db)):
    settings = get_shop_settings(db)
    return templates.TemplateResponse(request=request, name="profile.html", context={
        "request": request,
        "user": user,
        "settings": settings,
        "message": request.query_params.get("message"),
        "error": request.query_params.get("error")
    })

@router.post("/profile")
def profile_update(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    current_password: str = Form(None),
    new_password: str = Form(None),
    confirm_password: str = Form(None),
    user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    user.name = name.strip()
    user.email = email.strip()
    user.phone = phone.strip() if phone else None

    if new_password:
        if not current_password or not user.check_password(current_password):
            return RedirectResponse(url="/profile?error=Current+password+is+incorrect", status_code=status.HTTP_302_FOUND)
        if new_password != confirm_password:
            return RedirectResponse(url="/profile?error=New+passwords+do+not+match", status_code=status.HTTP_302_FOUND)
        if len(new_password) < 6:
            return RedirectResponse(url="/profile?error=Password+must+be+at+least+6+characters", status_code=status.HTTP_302_FOUND)
        user.set_password(new_password)

    db.commit()
    request.session["user_name"] = user.name
    log_activity(db, action="Profile Updated", module="Profile", record_id=user.id, details="User updated profile details.", user=user, request=request)

    return RedirectResponse(url="/profile?message=Profile+updated+successfully", status_code=status.HTTP_302_FOUND)
