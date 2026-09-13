from decimal import Decimal
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from marshmallow import ValidationError as MarshmallowValidationError
from sqlalchemy import or_, and_, desc
from app.extensions import db, limiter
from app.models.domain import Account, Transaction, UserRole, TransactionStatus
from app.schemas.transfer_schema import TransferRequestSchema, TransactionFilterSchema
from app.services.transfer_service import execute_transfer
from app.core.exceptions import (
    InsufficientBalanceError,
    AccountNotFoundError,
    AccountInactiveError,
    InvalidTransferError,
    IdempotencyKeyConflictError,
    TransferError
)

transfer_bp = Blueprint("transfers", __name__, url_prefix="/api/v1/transfers")
transfer_request_schema = TransferRequestSchema()
filter_schema = TransactionFilterSchema()


def get_current_user_and_role():
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    role = claims.get("role", "CUSTOMER")
    return user_id, role


@transfer_bp.route("", methods=["POST"])
@jwt_required()
@limiter.limit("30/minute")
def create_transfer():
    """
    Executes a secure, atomic transfer between two accounts.
    Sender ownership is strictly verified via uniform 404 defense.
    Receiver status & funds balance are verified under lock in transfer_service.
    """
    user_id, role = get_current_user_and_role()
    data = request.get_json() or {}

    try:
        validated_data = transfer_request_schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    sender_id = validated_data["sender_account_id"]
    receiver_id = validated_data["receiver_account_id"]
    amount = Decimal(str(validated_data["amount"]))
    idempotency_key = validated_data.get("idempotency_key")

    # Account Enumeration Defense: Verify sender ownership in route layer
    sender_account = Account.query.filter_by(account_id=sender_id).first()
    if not sender_account or (sender_account.user_id != user_id and role != UserRole.ADMIN.value):
        return jsonify({"error": f"Account with ID {sender_id} not found."}), 404

    try:
        tx = execute_transfer(
            db_session=db.session,
            sender_id=sender_id,
            receiver_id=receiver_id,
            amount=amount,
            idempotency_key=idempotency_key
        )
        return jsonify({
            "message": "Transfer executed successfully.",
            "transaction": tx.to_dict()
        }), 201

    except AccountNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except InsufficientBalanceError as e:
        return jsonify({"error": str(e)}), 400
    except AccountInactiveError as e:
        return jsonify({"error": str(e)}), 400
    except InvalidTransferError as e:
        return jsonify({"error": str(e)}), 400
    except IdempotencyKeyConflictError as e:
        return jsonify({"error": str(e)}), 409
    except TransferError as e:
        return jsonify({"error": "Transfer processing error", "details": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "Unexpected server error during transfer", "details": str(e)}), 500


@transfer_bp.route("/history", methods=["GET"])
@jwt_required()
def get_transaction_history():
    """
    Returns paginated transaction history.
    Customers see all transactions involving their accounts.
    Admins can view transactions across all accounts or filter by account.
    """
    user_id, role = get_current_user_and_role()
    
    # Query parameters
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 100)
    status_filter = request.args.get("status")
    type_filter = request.args.get("type", "ALL").upper()
    target_account_id = request.args.get("account_id", type=int)

    # Determine eligible account IDs for this user
    user_accounts = Account.query.filter_by(user_id=user_id).all()
    user_account_ids = [acc.account_id for acc in user_accounts]

    query = Transaction.query

    if role == UserRole.ADMIN.value:
        if target_account_id:
            if type_filter == "SENT":
                query = query.filter(Transaction.sender_account_id == target_account_id)
            elif type_filter == "RECEIVED":
                query = query.filter(Transaction.receiver_account_id == target_account_id)
            else:
                query = query.filter(
                    or_(
                        Transaction.sender_account_id == target_account_id,
                        Transaction.receiver_account_id == target_account_id
                    )
                )
    else:
        if not user_account_ids:
            return jsonify({
                "transactions": [],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_items": 0,
                    "total_pages": 0
                }
            }), 200

        if target_account_id:
            # Check ownership
            if target_account_id not in user_account_ids:
                return jsonify({"error": f"Account with ID {target_account_id} not found."}), 404
            
            if type_filter == "SENT":
                query = query.filter(Transaction.sender_account_id == target_account_id)
            elif type_filter == "RECEIVED":
                query = query.filter(Transaction.receiver_account_id == target_account_id)
            else:
                query = query.filter(
                    or_(
                        Transaction.sender_account_id == target_account_id,
                        Transaction.receiver_account_id == target_account_id
                    )
                )
        else:
            if type_filter == "SENT":
                query = query.filter(Transaction.sender_account_id.in_(user_account_ids))
            elif type_filter == "RECEIVED":
                query = query.filter(Transaction.receiver_account_id.in_(user_account_ids))
            else:
                query = query.filter(
                    or_(
                        Transaction.sender_account_id.in_(user_account_ids),
                        Transaction.receiver_account_id.in_(user_account_ids)
                    )
                )

    if status_filter:
        try:
            status_enum = TransactionStatus(status_filter.upper())
            query = query.filter(Transaction.status == status_enum)
        except ValueError:
            pass

    # Order by newest first
    query = query.order_by(desc(Transaction.created_at))

    total_items = query.count()
    total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 0
    paginated_transactions = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        "transactions": [tx.to_dict() for tx in paginated_transactions],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_items": total_items,
            "total_pages": total_pages
        }
    }), 200
