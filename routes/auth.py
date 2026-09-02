from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User
from utils.auth_helper import get_current_user, require_login, get_shop_settings
from utils.audit_helper import log_activity
from utils.rate_limit import client_ip, register_failure, reset, seconds_until_unblocked
from utils.templating import templates

router = APIRouter(tags=["auth"])

MIN_PASSWORD_LENGTH = 6

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    settings = get_shop_settings(db)
    return templates.TemplateResponse(request=request, name="auth/login.html", context={
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
    username = username.strip()
    ip = client_ip(request)

    blocked_for = seconds_until_unblocked(ip, username)
    if blocked_for:
        minutes = max(1, blocked_for // 60)
        return templates.TemplateResponse(request=request, name="auth/login.html", context={
            "settings": settings,
            "error": f"Too many failed login attempts. Please try again in about {minutes} minute(s).",
            "username": username
        }, status_code=429)

    user = db.query(User).filter(
        (User.username == username) | (User.email == username)
    ).first()

    # A single generic message for both "no such user" and "wrong password" so
    # the form cannot be used to enumerate valid usernames.
    if not user or not user.check_password(password):
        remaining = register_failure(ip, username)
        error = "Invalid username/email or password."
        if remaining and remaining <= 3:
            error += f" {remaining} attempt(s) remaining before a temporary lockout."
        return templates.TemplateResponse(request=request, name="auth/login.html", context={
            "settings": settings,
            "error": error,
            "username": username
        }, status_code=400)

    if user.status != "active":
        register_failure(ip, username)
        return templates.TemplateResponse(request=request, name="auth/login.html", context={
            "settings": settings,
            "error": "Your account has been deactivated. Please contact the owner.",
            "username": username
        }, status_code=403)

    reset(ip, username)

    # Rotate the session on privilege change to prevent session fixation: an
    # attacker-planted pre-login cookie must not carry over into the new session.
    request.session.clear()
    request.session["user_id"] = user.id
    request.session["user_role"] = user.role
    request.session["user_name"] = user.name

    log_activity(db, action="User Login", module="Auth", record_id=user.id, details=f"User {user.username} logged in successfully.", user=user, request=request)

    return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        log_activity(db, action="User Logout", module="Auth", record_id=user.id, details=f"User {user.username} logged out.", user=user, request=request)
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request, user: User = Depends(require_login), db: Session = Depends(get_db)):
    settings = get_shop_settings(db)
    return templates.TemplateResponse(request=request, name="profile.html", context={
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
    name = name.strip()
    email = email.strip()
    if not name:
        return RedirectResponse(url="/profile?error=Name+is+required", status_code=status.HTTP_303_SEE_OTHER)
    if not email:
        return RedirectResponse(url="/profile?error=Email+is+required", status_code=status.HTTP_303_SEE_OTHER)

    # `email` is unique; committing a duplicate would raise an IntegrityError 500.
    clash = db.query(User).filter(User.email == email, User.id != user.id).first()
    if clash:
        return RedirectResponse(url="/profile?error=That+email+is+already+in+use", status_code=status.HTTP_303_SEE_OTHER)

    if new_password:
        if not current_password or not user.check_password(current_password):
            return RedirectResponse(url="/profile?error=Current+password+is+incorrect", status_code=status.HTTP_303_SEE_OTHER)
        if new_password != confirm_password:
            return RedirectResponse(url="/profile?error=New+passwords+do+not+match", status_code=status.HTTP_303_SEE_OTHER)
        if len(new_password) < MIN_PASSWORD_LENGTH:
            return RedirectResponse(url=f"/profile?error=Password+must+be+at+least+{MIN_PASSWORD_LENGTH}+characters", status_code=status.HTTP_303_SEE_OTHER)
        user.set_password(new_password)

    user.name = name
    user.email = email
    user.phone = phone.strip() if phone else None

    db.commit()
    request.session["user_name"] = user.name
    log_activity(db, action="Profile Updated", module="Profile", record_id=user.id, details="User updated profile details.", user=user, request=request)

    return RedirectResponse(url="/profile?message=Profile+updated+successfully", status_code=status.HTTP_303_SEE_OTHER)
