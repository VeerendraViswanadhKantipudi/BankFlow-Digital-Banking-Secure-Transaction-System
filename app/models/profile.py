"""
UserProfile model — KYC-lite customer profile extension.

Stores the structured identity fields required for a minimal KYC workflow.
Separate from the core User model to preserve the existing auth/account logic.
A bank can bolt real verification (document upload, OTP) onto kyc_status later.

One-to-one with User (one profile per user, created at registration).
"""
import enum
from datetime import datetime, timezone
from app.extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class KycStatus(str, enum.Enum):
    PENDING = "PENDING"      # Submitted, awaiting review
    VERIFIED = "VERIFIED"    # Admin has verified the identity
    REJECTED = "REJECTED"    # Admin has rejected (e.g. ID mismatch)


class IdType(str, enum.Enum):
    AADHAAR = "AADHAAR"
    PASSPORT = "PASSPORT"
    PAN = "PAN"
    OTHER = "OTHER"


class UserProfile(db.Model):
    """
    KYC-lite identity profile.
    Fields intentionally kept at the minimum a bank needs to onboard a customer
    and pass a basic AML/KYC compliance gate — more fields can be added later.
    """
    __tablename__ = "user_profiles"

    profile_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Contact
    phone_number = db.Column(db.String(20), nullable=True)

    # Identity (KYC-lite)
    date_of_birth = db.Column(db.Date, nullable=True)           # ISO 8601 date
    id_type = db.Column(
        db.Enum(IdType, name="id_type_enum", native_enum=False),
        nullable=True
    )
    id_number = db.Column(db.String(64), nullable=True)          # Not stored in plaintext ideally, but out-of-scope here

    # Address
    address_line1 = db.Column(db.String(255), nullable=True)
    address_city = db.Column(db.String(100), nullable=True)
    address_country = db.Column(db.String(64), nullable=True)

    # KYC review status — set by admin, not customer
    kyc_status = db.Column(
        db.Enum(KycStatus, name="kyc_status_enum", native_enum=False),
        default=KycStatus.PENDING,
        nullable=False
    )

    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=True)

    # Relationship back to user
    user = db.relationship("User", backref=db.backref("profile", uselist=False, lazy=True))

    def to_dict(self):
        return {
            "profile_id": self.profile_id,
            "user_id": self.user_id,
            "phone_number": self.phone_number,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "id_type": self.id_type.value if isinstance(self.id_type, IdType) else self.id_type,
            "id_number": self.id_number,
            "address_line1": self.address_line1,
            "address_city": self.address_city,
            "address_country": self.address_country,
            "kyc_status": self.kyc_status.value if isinstance(self.kyc_status, KycStatus) else self.kyc_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

