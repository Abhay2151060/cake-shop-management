from sqlalchemy.orm import Session
from models import AuditLog, User
from fastapi import Request

def log_activity(
    db: Session,
    action: str,
    module: str,
    record_id: str = None,
    details: str = None,
    user: User = None,
    request: Request = None
):
    ip_addr = "127.0.0.1"
    if request and request.client:
        ip_addr = request.client.host

    user_id = user.id if user else None
    user_name = user.name if user else "System"
    role = user.role if user else "system"

    audit_entry = AuditLog(
        user_id=user_id,
        user_name=user_name,
        role=role,
        action=action,
        module=module,
        record_id=str(record_id) if record_id else None,
        details=details,
        ip_address=ip_addr
    )
    db.add(audit_entry)
    db.commit()
