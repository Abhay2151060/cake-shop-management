from functools import wraps
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User, Setting

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id, User.status == "active").first()
    return user

def require_login(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"}
        )
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
    settings_dict = {s.key: s.value for s in settings_records}
    return settings_dict
