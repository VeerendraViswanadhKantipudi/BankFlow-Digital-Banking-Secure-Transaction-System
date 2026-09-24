"""
Statement download routes.

GET /api/v1/statements/<account_id>/csv
  — Downloads CSV of all transactions (or date-filtered) for the account.

GET /api/v1/statements/<account_id>/pdf
  — Downloads PDF statement for the account.

GET /api/v1/statements/receipt/<transaction_id>/pdf
  — Downloads a single-page PDF receipt for a specific transaction.

Query params for account statements (all optional):
  from_date=YYYY-MM-DD  — start of date range (inclusive)
  to_date=YYYY-MM-DD    — end of date range (inclusive)
"""
from datetime import datetime, timezone
from flask import Blueprint, request, Response
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.extensions import db
from app.models.domain import UserRole
from app.models.branding import BankConfig
from app.services.statement_service import (
    generate_csv_statement,
    generate_pdf_statement,
    generate_pdf_receipt,
)
from app.core.exceptions import ResourceNotFoundError, ForbiddenError

statement_bp = Blueprint("statements", __name__, url_prefix="/api/v1/statements")

_DATE_FMT = "%Y-%m-%d"


def _parse_date(param_name: str):
    raw = request.args.get(param_name)
    if not raw:
        return None
    try:
        return datetime.strptime(raw, _DATE_FMT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _get_role_and_user():
    claims = get_jwt()
    user_id = int(get_jwt_identity())
    is_admin = claims.get("role") == UserRole.ADMIN.value
    return user_id, is_admin


def _bank_name() -> str:
    config = BankConfig.effective_config()
    return config.get("bank_name", "BankFlow")


@statement_bp.route("/<int:account_id>/csv", methods=["GET"])
@jwt_required()
def download_csv(account_id: int):
    """Downloads a CSV account statement."""
    user_id, is_admin = _get_role_and_user()
    from_date = _parse_date("from_date")
    to_date = _parse_date("to_date")

    try:
        csv_bytes = generate_csv_statement(
            db_session=db.session,
            user_id=user_id,
            account_id=account_id,
            is_admin=is_admin,
            from_date=from_date,
            to_date=to_date,
        )
    except ResourceNotFoundError as e:
        from flask import jsonify
        return jsonify({"error": str(e)}), 404
    except ForbiddenError as e:
        from flask import jsonify
        return jsonify({"error": str(e)}), 403

    filename = f"statement_acct{account_id}.csv"
    return Response(
        csv_bytes,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/csv; charset=utf-8",
        }
    )


@statement_bp.route("/<int:account_id>/pdf", methods=["GET"])
@jwt_required()
def download_pdf(account_id: int):
    """Downloads a PDF account statement."""
    user_id, is_admin = _get_role_and_user()
    from_date = _parse_date("from_date")
    to_date = _parse_date("to_date")

    try:
        pdf_bytes = generate_pdf_statement(
            db_session=db.session,
            user_id=user_id,
            account_id=account_id,
            is_admin=is_admin,
            bank_name=_bank_name(),
            from_date=from_date,
            to_date=to_date,
        )
    except ResourceNotFoundError as e:
        from flask import jsonify
        return jsonify({"error": str(e)}), 404
    except ForbiddenError as e:
        from flask import jsonify
        return jsonify({"error": str(e)}), 403

    filename = f"statement_acct{account_id}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        }
    )


@statement_bp.route("/receipt/<int:transaction_id>/pdf", methods=["GET"])
@jwt_required()
def download_receipt_pdf(transaction_id: int):
    """Downloads a single-page PDF receipt for a transaction."""
    user_id, is_admin = _get_role_and_user()

    try:
        pdf_bytes = generate_pdf_receipt(
            db_session=db.session,
            user_id=user_id,
            transaction_id=transaction_id,
            is_admin=is_admin,
            bank_name=_bank_name(),
        )
    except ResourceNotFoundError as e:
        from flask import jsonify
        return jsonify({"error": str(e)}), 404
    except ForbiddenError as e:
        from flask import jsonify
        return jsonify({"error": str(e)}), 403

    filename = f"receipt_tx{transaction_id}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        }
    )

