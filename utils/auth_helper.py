from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User, Setting


class RedirectToLogin(HTTPException):
    """
    Signals "not authenticated" as a browser redirect.

    303 (rather than the previous 307) so the browser re-issues the follow-up as
    a GET; a 307 made unauthenticated POSTs redirect into `POST /login`, which
    then failed on missing form fields instead of showing the login page.
    """

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"}
        )


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id, User.status == "active").first()
    if user is None:
        # The account was deleted or deactivated while the session was still
        # valid: drop the stale session so the user is cleanly logged out.
        request.session.clear()
    return user


def require_login(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_current_user(request, db)
    if not user:
        raise RedirectToLogin()
    return user


def require_owner(request: Request, db: Session = Depends(get_db)) -> User:
    user = require_login(request, db)
    if user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Owner role required."
        )
    return user


def require_staff(request: Request, db: Session = Depends(get_db)) -> User:
    user = require_login(request, db)
    # Both staff and owner can access staff endpoints
    if user.role not in ["staff", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden."
        )
    return user


def get_shop_settings(db: Session) -> dict:
    settings_records = db.query(Setting).all()
    return {s.key: s.value for s in settings_records}
