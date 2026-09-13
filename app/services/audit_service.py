import json
import logging
from typing import Optional, Any, Dict
from flask import has_request_context, has_app_context, request, g
from sqlalchemy.orm import Session
from app.extensions import db
from app.models.domain import AuditLog, AuditEventType

logger = logging.getLogger(__name__)


def record_audit_event(
    event_type: AuditEventType,
    actor_id: Optional[int] = None,
    target_user_id: Optional[int] = None,
    target_account_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None,
    db_session: Optional[Session] = None
) -> Optional[AuditLog]:
    """
    Appends an immutable audit event record to the audit_logs table.
    Captures HTTP context (IP, User-Agent, X-Request-ID) automatically if running in request scope.
    """
    if has_request_context():
        try:
            if ip_address is None:
                ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
            if user_agent is None:
                user_agent = request.headers.get("User-Agent", "")[:255]
            if request_id is None:
                request_id = getattr(g, "request_id", None) or request.headers.get("X-Request-ID")
        except Exception as e:
            logger.debug(f"Could not extract request headers for audit log: {e}")

    details_serialized = json.dumps(details, default=str) if details else None

    audit_entry = AuditLog(
        event_type=event_type,
        actor_id=actor_id,
        target_user_id=target_user_id,
        target_account_id=target_account_id,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
        details_json=details_serialized
    )
    
    if db_session is not None:
        db_session.add(audit_entry)
    elif has_app_context():
        db.session.add(audit_entry)
    
    return audit_entry

