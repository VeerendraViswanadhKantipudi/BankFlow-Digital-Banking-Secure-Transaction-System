import json
from decimal import Decimal
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from marshmallow import ValidationError as MarshmallowValidationError
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models.domain import (
    Account,User,Transaction,AccountStatus,UserRole,TransactionStatus,LedgerEntry,LedgerEntryType,AuditLog,AuditEventType)
    Account, User, Transaction, AccountStatus, UserRole, TransactionStatus,
    LedgerEntry, LedgerEntryType, AuditLog, AuditEventType)
from app.models.idempotency import IdempotencyRecord
from app.schemas.account_schema import CreateAccountSchema, UpdateAccountStatusSchema, UpdateUserRoleSchema, DepositSchema
from app.schemas.transfer_schema import TransactionFilterSchema
from app.services.auth_service import generate_account_number
from app.services.audit_service import record_audit_event
from app.services.reconciliation_service import reconcile_system_balances


account_bp = Blueprint("accounts", __name__, url_prefix="/api/v1/accounts")
create_account_schema = CreateAccountSchema()
update_status_schema = UpdateAccountStatusSchema()
update_role_schema = UpdateUserRoleSchema()
deposit_schema = DepositSchema()
filter_schema = TransactionFilterSchema()


def get_current_user_and_role():
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    role = claims.get("role", "CUSTOMER")
    return user_id, role


@account_bp.route("", methods=["GET"])
@jwt_required()
def list_accounts():
    """
    Lists accounts owned by the authenticated user, or all accounts if the caller is an ADMIN.
    Non-admin users can only view their own accounts.
    """
    user_id, role = get_current_user_and_role()
    if role == UserRole.ADMIN.value:
        accounts = Account.query.order_by(Account.account_id).all()
    else:
        accounts = Account.query.filter_by(user_id=user_id).order_by(Account.account_id).all()
    
    return jsonify({
        "accounts": [acc.to_dict() for acc in accounts]
    }), 200


@account_bp.route("/<int:account_id>", methods=["GET"])
@jwt_required()
def get_account(account_id: int):
    """
    Retrieves account details by numerical account ID.
    
    Security Defense — Account Enumeration Prevention:
    Returns a uniform 404 response if:
    1. The account ID does not exist in the database, OR
    2. The account exists but belongs to a different user (and caller is not an ADMIN).
    """
    user_id, role = get_current_user_and_role()
    account = Account.query.filter_by(account_id=account_id).first()

    # Uniform 404 response to prevent account ID probing/enumeration
    if not account or (account.user_id != user_id and role != UserRole.ADMIN.value):
        return jsonify({"error": f"Account with ID {account_id} not found."}), 404

    return jsonify({"account": account.to_dict()}), 200


# Helper: idempotency check + record write
def _check_idempotency(idem_key: str, endpoint: str):
    """
    Returns (record, response) if a replay is found, else (None, None).
    Raises 409 if key exists for a different endpoint.
    """
    if not idem_key:
        return None, None
    existing = IdempotencyRecord.query.filter_by(idempotency_key=idem_key).first()
    if existing:
        if existing.endpoint != endpoint:
            return "conflict", None
        body = json.loads(existing.response_body_json)
        return "replay", (body, existing.status_code)
    return None, None


def _store_idempotency(idem_key: str, endpoint: str, body: dict, status_code: int):
    """Stores a new IdempotencyRecord. Call after successful commit."""
    if not idem_key:
        return
    record = IdempotencyRecord(
        idempotency_key=idem_key,
        endpoint=endpoint,
        response_body_json=json.dumps(body, default=str),
        status_code=status_code
    )
    try:
        db.session.add(record)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()  # Race: another request stored same key first — that's fine


@account_bp.route("", methods=["POST"])
@jwt_required()
def create_account():
    """Creates a secondary account for the authenticated user."""
    """Creates a secondary account for the authenticated user.

    Supports Idempotency-Key header: send the same request with the same key twice
    and the second call returns the original response without creating a second account.
    """
    user_id, _ = get_current_user_and_role()
    idem_key = request.headers.get("Idempotency-Key") or request.headers.get("X-Idempotency-Key")
    endpoint = "create_account"

    state, replay = _check_idempotency(idem_key, endpoint)
    if state == "conflict":
        return jsonify({"error": "Idempotency key conflict: key used for a different endpoint."}), 409
    if state == "replay":
        body, status_code = replay
        return jsonify(body), status_code

    data = request.get_json() or {}
    
    try:
        validated_data = create_account_schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    initial_deposit = Decimal(str(validated_data.get("initial_deposit", "0.00")))
    account_number = generate_account_number()
    try:
        account_number = generate_account_number()
    except Exception as e:
        return jsonify({"error": str(e)}), 503

    account = Account(
        user_id=user_id,
        account_number=account_number,
        balance=initial_deposit,
        status=AccountStatus.ACTIVE
    )
    db.session.add(account)
    db.session.flush()

    # Record initial deposit ledger entry if > 0
    if initial_deposit > 0:
        ledger = LedgerEntry(
            account_id=account.account_id,
            entry_type=LedgerEntryType.CREDIT,
            amount=initial_deposit,
            balance_after=initial_deposit,
            description="Initial account creation deposit"
        )
        db.session.add(ledger)

    record_audit_event(
        event_type=AuditEventType.ACCOUNT_CREATED,
        actor_id=user_id,
        target_account_id=account.account_id,
        details={"account_number": account_number, "initial_deposit": str(initial_deposit)}
    )

    db.session.commit()

    return jsonify({
    response_body = {
        "message": "Account created successfully.",
        "account": account.to_dict()
    }), 201
    }
    _store_idempotency(idem_key, endpoint, response_body, 201)

    return jsonify(response_body), 201



@account_bp.route("/<int:account_id>/deposit", methods=["POST"])
@jwt_required()
def deposit_funds(account_id: int):
    """Adds funds to an account and writes a CREDIT ledger entry."""
    """Adds funds to an account and writes a CREDIT ledger entry.

    Supports Idempotency-Key header: replaying the same deposit request with the same key
    returns the original response without applying a second credit to the account.
    """
    user_id, role = get_current_user_and_role()
    idem_key = request.headers.get("Idempotency-Key") or request.headers.get("X-Idempotency-Key")
    endpoint = f"deposit_funds:{account_id}"

    state, replay = _check_idempotency(idem_key, endpoint)
    if state == "conflict":
        return jsonify({"error": "Idempotency key conflict: key used for a different endpoint."}), 409
    if state == "replay":
        body, status_code = replay
        return jsonify(body), status_code

    account = Account.query.filter_by(account_id=account_id).first()

    if not account or (account.user_id != user_id and role != UserRole.ADMIN.value):
        return jsonify({"error": f"Account with ID {account_id} not found."}), 404

    if account.status != AccountStatus.ACTIVE:
        return jsonify({"error": f"Account is {account.status.value}. Only ACTIVE accounts can receive deposits."}), 400

    data = request.get_json() or {}
    try:
        validated_data = deposit_schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    amount = Decimal(str(validated_data["amount"]))
    new_balance = Decimal(str(account.balance)) + amount
    account.balance = new_balance

    # Record general ledger credit entry
    ledger = LedgerEntry(
        account_id=account_id,
        entry_type=LedgerEntryType.CREDIT,
        amount=amount,
        balance_after=new_balance,
        description=f"External deposit into Account #{account_id}"
    )
    db.session.add(ledger)

    # Record audit log
    record_audit_event(
        event_type=AuditEventType.DEPOSIT_COMPLETED,
        actor_id=user_id,
        target_account_id=account_id,
        details={"amount": str(amount), "new_balance": str(new_balance)}
    )

    db.session.commit()

    return jsonify({
    response_body = {
        "message": f"Successfully deposited {amount} into account {account_id}.",
        "account": account.to_dict()
    }), 200
    }
    _store_idempotency(idem_key, endpoint, response_body, 200)

    return jsonify(response_body), 200



@account_bp.route("/<int:account_id>/status", methods=["PATCH"])
@jwt_required()
def update_account_status(account_id: int):
    """Admin-only endpoint: Freeze, Unfreeze (ACTIVE), or CLOSE an account."""
    user_id, role = get_current_user_and_role()
    if role != UserRole.ADMIN.value:
        return jsonify({"error": "Admin privilege required to modify account status."}), 403

    account = Account.query.filter_by(account_id=account_id).first()
    if not account:
        return jsonify({"error": f"Account with ID {account_id} not found."}), 404

    data = request.get_json() or {}
    try:
        validated_data = update_status_schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    old_status = account.status.value if hasattr(account.status, 'value') else str(account.status)
    new_status = AccountStatus(validated_data["status"])
    account.status = new_status

    record_audit_event(
        event_type=AuditEventType.ACCOUNT_STATUS_CHANGED,
        actor_id=user_id,
        target_account_id=account_id,
        details={"old_status": old_status, "new_status": new_status.value}
    )

    db.session.commit()

    return jsonify({
        "message": f"Account {account_id} status updated to {new_status.value}.",
        "account": account.to_dict()
    }), 200


@account_bp.route("/admin/users", methods=["GET"])
@jwt_required()
def list_all_users_admin():
    """Admin endpoint to view all system users and their accounts."""
    _, role = get_current_user_and_role()
    if role != UserRole.ADMIN.value:
        return jsonify({"error": "Admin privilege required."}), 403

    users = User.query.order_by(User.user_id).all()
    results = []
    for u in users:
        u_dict = u.to_dict()
        u_dict["accounts"] = [acc.to_dict() for acc in u.accounts]
        results.append(u_dict)

    return jsonify({"users": results}), 200


@account_bp.route("/admin/users/<int:user_id>/role", methods=["PATCH"])
@jwt_required()
def update_user_role(user_id: int):
    """Admin-only endpoint: Promote user to ADMIN or demote to CUSTOMER."""
    actor_id, role = get_current_user_and_role()
    if role != UserRole.ADMIN.value:
        return jsonify({"error": "Admin privilege required to modify user roles."}), 403

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": f"User with ID {user_id} not found."}), 404

    data = request.get_json() or {}
    try:
        validated_data = update_role_schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    old_role = user.role.value if hasattr(user.role, 'value') else str(user.role)
    new_role = UserRole(validated_data["role"])
    user.role = new_role

    record_audit_event(
        event_type=AuditEventType.ROLE_UPDATED,
        actor_id=actor_id,
        target_user_id=user_id,
        details={"old_role": old_role, "new_role": new_role.value}
    )

    db.session.commit()

    return jsonify({
        "message": f"User {user_id} role updated to {new_role.value}.",
        "user": user.to_dict()
    }), 200


@account_bp.route("/admin/audit-logs", methods=["GET"])
@jwt_required()
def list_audit_logs():
    """Admin-only endpoint: Retrieve paginated immutable security audit logs."""
    _, role = get_current_user_and_role()
    if role != UserRole.ADMIN.value:
        return jsonify({"error": "Admin privilege required."}), 403

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    event_filter = request.args.get("event_type")

    query = AuditLog.query
    if event_filter:
        try:
            event_enum = AuditEventType(event_filter.upper())
            query = query.filter_by(event_type=event_enum)
        except ValueError:
            pass

    query = query.order_by(desc(AuditLog.created_at))
    total_items = query.count()
    total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 0
    logs = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        "audit_logs": [log.to_dict() for log in logs],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_items": total_items,
            "total_pages": total_pages
        }
    }), 200


@account_bp.route("/admin/reconcile", methods=["GET"])
@jwt_required()
def run_reconciliation():
    """Admin-only endpoint: Execute live system-wide financial ledger reconciliation."""
    _, role = get_current_user_and_role()
    if role != UserRole.ADMIN.value:
        return jsonify({"error": "Admin privilege required."}), 403

    report = reconcile_system_balances(db.session)
    return jsonify({
        "reconciliation": report
    }), 200

