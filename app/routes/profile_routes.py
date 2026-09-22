"""
Profile API routes — KYC-lite customer profile management.

GET  /api/v1/profile          — authenticated user's own profile
PATCH /api/v1/profile         — update own phone/address fields
GET  /api/v1/profile/kyc-status/<user_id>  — admin-only: view any user's KYC status
PATCH /api/v1/profile/kyc-status/<user_id> — admin-only: set kyc_status (PENDING/VERIFIED/REJECTED)
"""
from datetime import date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from marshmallow import Schema, fields as ma_fields, validate, validates, ValidationError as MaValidationError
from app.extensions import db
from app.models.domain import UserRole
from app.models.profile import UserProfile, KycStatus, IdType

profile_bp = Blueprint("profile", __name__, url_prefix="/api/v1/profile")


class ProfilePatchSchema(Schema):
    phone_number = ma_fields.Str(validate=validate.Length(max=20), load_default=None)
    date_of_birth = ma_fields.Date(load_default=None)  # ISO 8601
    id_type = ma_fields.Str(
        validate=validate.OneOf([t.value for t in IdType]),
        load_default=None
    )
    id_number = ma_fields.Str(validate=validate.Length(max=64), load_default=None)
    address_line1 = ma_fields.Str(validate=validate.Length(max=255), load_default=None)
    address_city = ma_fields.Str(validate=validate.Length(max=100), load_default=None)
    address_country = ma_fields.Str(validate=validate.Length(max=64), load_default=None)

    @validates("date_of_birth")
    def validate_dob(self, value, **kwargs):
        if value and value > date.today():
            raise MaValidationError("Date of birth cannot be in the future.")


class KycStatusPatchSchema(Schema):
    kyc_status = ma_fields.Str(
        required=True,
        validate=validate.OneOf([s.value for s in KycStatus])
    )


_profile_patch_schema = ProfilePatchSchema()
_kyc_status_schema = KycStatusPatchSchema()

_PROFILE_FIELDS = [
    "phone_number", "date_of_birth", "id_type", "id_number",
    "address_line1", "address_city", "address_country"
]


def _get_or_create_profile(user_id: int) -> UserProfile:
    """Returns existing profile or creates a blank one for the user."""
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)
        db.session.flush()
    return profile


@profile_bp.route("", methods=["GET"])
@jwt_required()
def get_my_profile():
    """Returns the authenticated user's KYC profile (creates blank if first visit)."""
    user_id = int(get_jwt_identity())
    profile = _get_or_create_profile(user_id)
    db.session.commit()
    return jsonify({"profile": profile.to_dict()}), 200


@profile_bp.route("", methods=["PATCH"])
@jwt_required()
def update_my_profile():
    """Updates the authenticated user's editable profile fields."""
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    from marshmallow import ValidationError as MarshmallowValidationError
    try:
        validated = _profile_patch_schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    profile = _get_or_create_profile(user_id)

    for field in _PROFILE_FIELDS:
        value = validated.get(field)
        if value is not None:
            setattr(profile, field, value)

    db.session.commit()
    return jsonify({
        "message": "Profile updated successfully.",
        "profile": profile.to_dict()
    }), 200


@profile_bp.route("/kyc-status/<int:target_user_id>", methods=["GET"])
@jwt_required()
def get_user_kyc_status(target_user_id: int):
    """Admin-only: view any user's KYC status."""
    claims = get_jwt()
    if claims.get("role") != UserRole.ADMIN.value:
        return jsonify({"error": "Admin privilege required."}), 403

    profile = UserProfile.query.filter_by(user_id=target_user_id).first()
    if not profile:
        return jsonify({"error": f"No profile found for user {target_user_id}."}), 404

    return jsonify({"profile": profile.to_dict()}), 200


@profile_bp.route("/kyc-status/<int:target_user_id>", methods=["PATCH"])
@jwt_required()
def update_user_kyc_status(target_user_id: int):
    """Admin-only: set a user's KYC status (PENDING / VERIFIED / REJECTED)."""
    claims = get_jwt()
    if claims.get("role") != UserRole.ADMIN.value:
        return jsonify({"error": "Admin privilege required."}), 403

    data = request.get_json() or {}
    from marshmallow import ValidationError as MarshmallowValidationError
    try:
        validated = _kyc_status_schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    profile = UserProfile.query.filter_by(user_id=target_user_id).first()
    if not profile:
        return jsonify({"error": f"No profile found for user {target_user_id}."}), 404

    profile.kyc_status = KycStatus(validated["kyc_status"])
    db.session.commit()

    return jsonify({
        "message": f"KYC status for user {target_user_id} updated to {profile.kyc_status.value}.",
        "profile": profile.to_dict()
    }), 200

