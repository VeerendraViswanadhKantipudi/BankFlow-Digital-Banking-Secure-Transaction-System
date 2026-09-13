from datetime import datetime, timezone
from decimal import Decimal
import enum
from sqlalchemy import CheckConstraint, Index, Numeric
from app.extensions import db


class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"


class AccountStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    CLOSED = "CLOSED"


class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def utc_now():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.Enum(UserRole, name="user_role_enum", native_enum=False),
        default=UserRole.CUSTOMER,
        nullable=False
    )
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    accounts = db.relationship("Account", backref="user", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "full_name": self.full_name,
            "email": self.email,
            "role": self.role.value if isinstance(self.role, UserRole) else self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "accounts_count": len(self.accounts) if self.accounts else 0
        }


class Account(db.Model):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint("balance >= 0", name="check_account_balance_non_negative"),
    )

    account_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    account_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    balance = db.Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    status = db.Column(
        db.Enum(AccountStatus, name="account_status_enum", native_enum=False),
        default=AccountStatus.ACTIVE,
        nullable=False
    )
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    sent_transactions = db.relationship(
        "Transaction",
        foreign_keys="Transaction.sender_account_id",
        backref="sender_account",
        lazy="dynamic"
    )
    received_transactions = db.relationship(
        "Transaction",
        foreign_keys="Transaction.receiver_account_id",
        backref="receiver_account",
        lazy="dynamic"
    )

    def to_dict(self):
        return {
            "account_id": self.account_id,
            "user_id": self.user_id,
            "account_number": self.account_number,
            "balance": str(self.balance),
            "status": self.status.value if isinstance(self.status, AccountStatus) else self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Transaction(db.Model):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="check_transaction_amount_positive"),
        CheckConstraint("sender_account_id != receiver_account_id", name="check_sender_receiver_different"),
        Index("idx_tx_sender_created", "sender_account_id", "created_at"),
        Index("idx_tx_receiver_created", "receiver_account_id", "created_at"),
    )

    transaction_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_account_id = db.Column(db.Integer, db.ForeignKey("accounts.account_id"), nullable=False)
    receiver_account_id = db.Column(db.Integer, db.ForeignKey("accounts.account_id"), nullable=False)
    amount = db.Column(Numeric(12, 2), nullable=False)
    status = db.Column(
        db.Enum(TransactionStatus, name="transaction_status_enum", native_enum=False),
        default=TransactionStatus.PENDING,
        nullable=False
    )
    idempotency_key = db.Column(db.String(128), unique=True, nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)

    def to_dict(self):
        return {
            "transaction_id": self.transaction_id,
            "sender_account_id": self.sender_account_id,
            "receiver_account_id": self.receiver_account_id,
            "amount": str(self.amount),
            "status": self.status.value if isinstance(self.status, TransactionStatus) else self.status,
            "idempotency_key": self.idempotency_key,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class LedgerEntryType(str, enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class LedgerEntry(db.Model):
    """
    Double-Entry General Ledger record.
    Every financial event (transfer, deposit) records immutable balanced debit/credit lines.
    For transfers: exactly one DEBIT on sender and one CREDIT on receiver.
    Total Debits == Total Credits across the entire system.
    """
    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint("amount > 0", name="check_ledger_amount_positive"),
        Index("idx_ledger_account_created", "account_id", "created_at"),
        Index("idx_ledger_tx", "transaction_id"),
    )

    entry_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transactions.transaction_id", ondelete="CASCADE"), nullable=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.account_id", ondelete="CASCADE"), nullable=False)
    entry_type = db.Column(
        db.Enum(LedgerEntryType, name="ledger_entry_type_enum", native_enum=False),
        nullable=False
    )
    amount = db.Column(Numeric(12, 2), nullable=False)
    balance_after = db.Column(Numeric(12, 2), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    account = db.relationship("Account", backref="ledger_entries", lazy=True)
    transaction = db.relationship("Transaction", backref="ledger_entries", lazy=True)

    def to_dict(self):
        return {
            "entry_id": self.entry_id,
            "transaction_id": self.transaction_id,
            "account_id": self.account_id,
            "entry_type": self.entry_type.value if isinstance(self.entry_type, LedgerEntryType) else self.entry_type,
            "amount": str(self.amount),
            "balance_after": str(self.balance_after),
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class AuditEventType(str, enum.Enum):
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    USER_REGISTERED = "USER_REGISTERED"
    ROLE_UPDATED = "ROLE_UPDATED"
    ACCOUNT_CREATED = "ACCOUNT_CREATED"
    ACCOUNT_STATUS_CHANGED = "ACCOUNT_STATUS_CHANGED"
    DEPOSIT_COMPLETED = "DEPOSIT_COMPLETED"
    TRANSFER_COMPLETED = "TRANSFER_COMPLETED"
    RECONCILIATION_RUN = "RECONCILIATION_RUN"


class AuditLog(db.Model):
    """
    Append-only security and operational audit trail.
    Tracks authentication events, administrative role/status changes, and financial activities.
    """
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_event_created", "event_type", "created_at"),
        Index("idx_audit_actor_created", "actor_id", "created_at"),
    )

    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_type = db.Column(
        db.Enum(AuditEventType, name="audit_event_type_enum", native_enum=False),
        nullable=False
    )
    actor_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    target_user_id = db.Column(db.Integer, nullable=True)
    target_account_id = db.Column(db.Integer, nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    request_id = db.Column(db.String(64), nullable=True)
    details_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationship to acting user
    actor = db.relationship("User", foreign_keys=[actor_id], backref="audit_actions", lazy=True)

    def to_dict(self):
        return {
            "log_id": self.log_id,
            "event_type": self.event_type.value if isinstance(self.event_type, AuditEventType) else self.event_type,
            "actor_id": self.actor_id,
            "target_user_id": self.target_user_id,
            "target_account_id": self.target_account_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "details_json": self.details_json,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
