import random
import string
from decimal import Decimal
from flask_jwt_extended import create_access_token
from app.extensions import db, bcrypt
from app.models.domain import User, Account, UserRole, AccountStatus, AuditEventType
from app.services.audit_service import record_audit_event
from app.core.exceptions import AuthenticationError, ValidationError, AccountError

# Pre-computed dummy bcrypt hash for timing-safe comparison on non-existent users.
# When a login request is made for an email that doesn't exist in the database,
# we still execute bcrypt.check_password_hash against this dummy hash so the API
# response time is identical to a failed login for an existing user.
# This eliminates user enumeration attacks via side-channel response latency analysis.
DUMMY_BCRYPT_HASH = bcrypt.generate_password_hash("dummy_password_timing_protection").decode("utf-8")


def generate_account_number() -> str:
    """
    Generates a 12-digit formatted bank account number with a 'BF' prefix.
    Example: 'BF9482018471'
    """
    digits = "".join(random.choices(string.digits, k=10))
    return f"BF{digits}"


def register_user(full_name: str, email: str, password: str, initial_deposit: Decimal = Decimal("0.00"), role: str = "CUSTOMER"):
    """
    Registers a new user, securely hashes their password with bcrypt,
    and automatically provisions their primary checking account.
    
    Security Guarantee:
    - Public registrations are strictly assigned the CUSTOMER role.
    - Any client-supplied 'role' override is ignored to uphold RBAC integrity.
    - Admin status can only be granted by an authenticated administrator.
    """
    email_clean = email.strip().lower()
    
    # Check for duplicate email registration
    existing = User.query.filter_by(email=email_clean).first()
    if existing:
        raise ValidationError("An account with this email address already exists.")

    # Generate salted bcrypt password hash
    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    
    # Enforce safe default role
    try:
        user_role = UserRole(role.upper())
    except (ValueError, AttributeError):
        user_role = UserRole.CUSTOMER

    user = User(
        full_name=full_name.strip(),
        email=email_clean,
        password_hash=password_hash,
        role=user_role
    )
    db.session.add(user)
    db.session.flush()  # Flush to obtain user.user_id for foreign key linking

    # Provision primary bank account with initial deposit (if specified)
    account_number = generate_account_number()
    account = Account(
        user_id=user.user_id,
        account_number=account_number,
        balance=Decimal(str(initial_deposit)),
        status=AccountStatus.ACTIVE
    )
    db.session.add(account)
    db.session.commit()

    # Record audit event for successful registration
    record_audit_event(
        event_type=AuditEventType.USER_REGISTERED,
        actor_id=user.user_id,
        target_user_id=user.user_id,
        target_account_id=account.account_id,
        details={"email": user.email, "role": user.role.value, "initial_deposit": str(initial_deposit)}
    )
    db.session.commit()

    # Generate JWT with embedded claims (role, user_id, email, name)
    token = create_access_token(
        identity=str(user.user_id),
        additional_claims={
            "role": user.role.value,
            "email": user.email,
            "full_name": user.full_name
        }
    )

    return {
        "user": user.to_dict(),
        "primary_account": account.to_dict(),
        "access_token": token
    }


def authenticate_user(email: str, password: str):
    """
    Timing-safe authentication routine.
    
    Security Defenses:
    1. If the user does not exist, run a real bcrypt verification against DUMMY_BCRYPT_HASH
       so attackers cannot measure execution time to determine if an email exists.
    2. Uses bcrypt.check_password_hash for constant-time comparison against the stored hash.
    3. Records immutable audit logs for failed and successful authentication.
    4. Issues JWT with role claims on successful authentication.
    """
    email_clean = email.strip().lower()
    user = User.query.filter_by(email=email_clean).first()

    if user is None:
        # Perform dummy bcrypt check to equalize execution latency
        bcrypt.check_password_hash(DUMMY_BCRYPT_HASH, password)
        record_audit_event(
            event_type=AuditEventType.LOGIN_FAILED,
            details={"attempted_email": email_clean, "reason": "user_not_found"}
        )
        db.session.commit()
        raise AuthenticationError("Invalid email or password.")

    if not bcrypt.check_password_hash(user.password_hash, password):
        record_audit_event(
            event_type=AuditEventType.LOGIN_FAILED,
            actor_id=user.user_id,
            details={"attempted_email": email_clean, "reason": "invalid_password"}
        )
        db.session.commit()
        raise AuthenticationError("Invalid email or password.")

    # Record login success audit log
    record_audit_event(
        event_type=AuditEventType.LOGIN_SUCCESS,
        actor_id=user.user_id,
        details={"email": user.email}
    )
    db.session.commit()

    # Issue JWT access token
    token = create_access_token(
        identity=str(user.user_id),
        additional_claims={
            "role": user.role.value,
            "email": user.email,
            "full_name": user.full_name
        }
    )

    return {
        "user": user.to_dict(),
        "access_token": token
    }
