from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from marshmallow import ValidationError as MarshmallowValidationError
from app.extensions import db, limiter
from app.schemas.auth_schema import RegisterSchema, LoginSchema
from app.services.auth_service import register_user, authenticate_user
from app.core.exceptions import AuthenticationError, ValidationError
from app.models.domain import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")
register_schema = RegisterSchema()
login_schema = LoginSchema()


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("10/hour;5/minute")
def register():
    data = request.get_json() or {}
    try:
        validated_data = register_schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    try:
        # Public registration never accepts or processes role from client input (always CUSTOMER)
        result = register_user(
            full_name=validated_data["full_name"],
            email=validated_data["email"],
            password=validated_data["password"],
            initial_deposit=validated_data.get("initial_deposit", 0)
        )
        return jsonify({
            "message": "User registered successfully.",
            "data": result
        }), 201
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Registration failed", "details": str(e)}), 500


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("15/minute;50/hour")
def login():
    data = request.get_json() or {}
    try:
        validated_data = login_schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    try:
        result = authenticate_user(
            email=validated_data["email"],
            password=validated_data["password"]
        )
        return jsonify({
            "message": "Authentication successful.",
            "data": result
        }), 200
    except AuthenticationError as e:
        # Fire-and-forget login failure notification (never blocks the response)
        try:
            from app.services.notification_service import notify
            candidate_email = validated_data.get("email", "")
            if candidate_email:
                notify(
                    event="LOGIN_FAILED",
                    recipient_email=candidate_email,
                    context={"email": candidate_email, "reason": "Invalid credentials"},
                )
        except Exception:  # noqa: BLE001
            pass
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        return jsonify({"error": "Authentication error", "details": str(e)}), 500


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user_dict = user.to_dict()
    user_dict["accounts"] = [acc.to_dict() for acc in user.accounts]
    return jsonify({"user": user_dict}), 200
