"""
Idempotency Record model for BankFlow.

Provides HTTP-level idempotency for state-mutating endpoints beyond the transfer engine.
The transfer engine uses Transaction.idempotency_key directly; all other endpoints
(account creation, deposits) use this shared table.

Contract:
- On first request with key K: process normally, store response body + status in this table.
- On replay with same key K: return the stored response immediately, no re-execution.
- On key K with different endpoint: 409 Conflict.
"""
from datetime import datetime, timezone
from app.extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class IdempotencyRecord(db.Model):
    """
    Append-only cache of idempotent request outcomes.
    Written once on first successful execution; read on replay.
    Never updated or deleted by the application DB user.
    """
    __tablename__ = "idempotency_records"

    record_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # The client-supplied idempotency key (UUID recommended, max 128 chars)
    idempotency_key = db.Column(db.String(128), unique=True, nullable=False, index=True)

    # Endpoint identifier to detect cross-endpoint key reuse
    endpoint = db.Column(db.String(128), nullable=False)

    # Serialized JSON response body stored for replay
    response_body_json = db.Column(db.Text, nullable=False)

    # HTTP status code to replay
    status_code = db.Column(db.Integer, nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)

    def to_dict(self):
        return {
            "record_id": self.record_id,
            "idempotency_key": self.idempotency_key,
            "endpoint": self.endpoint,
            "status_code": self.status_code,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

