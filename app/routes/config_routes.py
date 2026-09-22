"""
BankConfig branding API routes.

GET  /api/v1/config/branding  — public, no auth required.
                                Returns effective branding config (DB → env → defaults).

PATCH /api/v1/config/branding — admin-only.
                                Merges supplied fields into the singleton BankConfig row.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from marshmallow import Schema, fields as ma_fields, validate
from app.extensions import db
from app.models.branding import BankConfig
from app.models.domain import UserRole, AuditEventType
from app.services.audit_service import record_audit_event

config_bp = Blueprint("config", __name__, url_prefix="/api/v1/config")


class BrandingPatchSchema(Schema):
    bank_name = ma_fields.Str(validate=validate.Length(max=120))
    bank_tagline = ma_fields.Str(validate=validate.Length(max=255))
    bank_logo_url = ma_fields.Url(require_tld=False, allow_none=True)
    primary_color = ma_fields.Str(validate=validate.Regexp(r'^#[0-9a-fA-F]{3,8}$'))
    secondary_color = ma_fields.Str(validate=validate.Regexp(r'^#[0-9a-fA-F]{3,8}$'))
    accent_color = ma_fields.Str(validate=validate.Regexp(r'^#[0-9a-fA-F]{3,8}$'))
    support_email = ma_fields.Email(allow_none=True)
    support_phone = ma_fields.Str(validate=validate.Length(max=40))
    bank_country = ma_fields.Str(validate=validate.Length(max=64))
    currency_code = ma_fields.Str(validate=validate.Length(min=3, max=8))
    currency_symbol = ma_fields.Str(validate=validate.Length(max=8))
    routing_number = ma_fields.Str(validate=validate.Length(max=20))
    swift_code = ma_fields.Str(validate=validate.Length(max=20))


_branding_patch_schema = BrandingPatchSchema()

_BRANDING_FIELDS = [
    "bank_name", "bank_tagline", "bank_logo_url",
    "primary_color", "secondary_color", "accent_color",
    "support_email", "support_phone", "bank_country",
    "currency_code", "currency_symbol", "routing_number", "swift_code",
]


@config_bp.route("/branding", methods=["GET"])
def get_branding():
    """
    Public endpoint — returns the effective white-label branding configuration.
    No authentication required: the frontend calls this before login to apply theming.
    """
    return jsonify({"branding": BankConfig.effective_config()}), 200


@config_bp.route("/branding", methods=["PATCH"])
@jwt_required()
def update_branding():
    """Admin-only endpoint — merges supplied fields into the singleton BankConfig row."""
    claims = get_jwt()
    role = claims.get("role", "CUSTOMER")
    if role != UserRole.ADMIN.value:
        return jsonify({"error": "Admin privilege required to update branding configuration."}), 403

    actor_id = int(get_jwt_identity())
    data = request.get_json() or {}

    from marshmallow import ValidationError as MarshmallowValidationError
    try:
        validated = _branding_patch_schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    if not validated:
        return jsonify({"error": "No branding fields supplied."}), 400

    row = BankConfig.get_or_create_singleton()

    changed_fields = {}
    for field in _BRANDING_FIELDS:
        if field in validated:
            old_val = getattr(row, field)
            new_val = validated[field]
            setattr(row, field, new_val)
            changed_fields[field] = {"from": old_val, "to": new_val}

    row.updated_by_user_id = actor_id

    record_audit_event(
        event_type=AuditEventType.BRANDING_UPDATED,
        actor_id=actor_id,
        details={"changed_fields": list(changed_fields.keys()), "changes": changed_fields}
    )

    db.session.commit()

    return jsonify({
        "message": "Branding configuration updated successfully.",
        "branding": row.to_dict()
    }), 200

