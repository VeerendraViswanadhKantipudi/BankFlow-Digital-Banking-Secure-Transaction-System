import os
import uuid
import click
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_limiter.errors import RateLimitExceeded
from app.core.config import Config
from app.db import validate_mysql_url
from app.extensions import db, jwt, bcrypt, limiter
from app.routes.auth_routes import auth_bp
from app.routes.account_routes import account_bp
from app.routes.transfer_routes import transfer_bp
from app.routes.config_routes import config_bp
from app.routes.profile_routes import profile_bp
from app.routes.statement_routes import statement_bp
# Import all models so db.create_all() registers every table
from app.models import domain  # noqa: F401  — registers User, Account, Transaction, LedgerEntry, AuditLog
from app.models import idempotency  # noqa: F401  — registers IdempotencyRecord
from app.models import branding  # noqa: F401  — registers BankConfig
from app.models import profile  # noqa: F401  — registers UserProfile


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 1. Enforce MySQL (InnoDB) check strictly at startup
    validate_mysql_url(app.config["SQLALCHEMY_DATABASE_URI"])

    # 2. Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    limiter.init_app(app)

    # 3. Initialize CORS with configured origins (not wildcard)
    CORS(app, resources={r"/api/.*": {"origins": app.config.get("CORS_ORIGINS", "*")}}, supports_credentials=True)

    # 4. Request Tracing Middleware (X-Request-ID)
    @app.before_request
    def set_request_id():
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        g.request_id = req_id

    @app.after_request
    def attach_request_id(response):
        if hasattr(g, "request_id"):
            response.headers["X-Request-ID"] = g.request_id
        return response

    # 5. Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(transfer_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(statement_bp)

    # 5b. Security Headers — applied to every response
    @app.after_request
    def add_security_headers(response):
        """
        Adds defensive HTTP security headers to every response.
        These prevent common browser-level attacks (XSS, clickjacking, MIME sniffing).
        """
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        # Prevent caching of authenticated API responses
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
        return response

    # 6. Root & Health routes
    @app.route("/", methods=["GET"])
    def root_index():
        return jsonify({
            "service": "BankFlow API",
            "status": "ONLINE",
            "health": "/api/v1/health"
        }), 200

    @app.route("/api/v1/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "HEALTHY",
            "service": "BankFlow API",
            "database_engine": "MySQL (InnoDB)",
            "version": "1.1.0",
            "request_id": getattr(g, "request_id", None)
        }), 200

    # 7. JWT Error Handlers
    @jwt.unauthorized_loader
    def unauthorized_callback(callback):
        return jsonify({
            "error": "Authorization token is missing.",
            "code": "AUTHORIZATION_HEADER_MISSING"
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(callback):
        return jsonify({
            "error": "Invalid authorization token signature.",
            "code": "INVALID_TOKEN"
        }), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "error": "The authorization token has expired.",
            "code": "TOKEN_EXPIRED"
        }), 401

    # 8. Rate Limit Error Handler
    @app.errorhandler(RateLimitExceeded)
    def handle_rate_limit_exceeded(e):
        return jsonify({
            "error": "Rate limit exceeded. Too many requests. Please try again later.",
            "code": "RATE_LIMIT_EXCEEDED",
            "details": str(e.description)
        }), 429

    # 9. Global 404, 500 and Exception handlers
    @app.errorhandler(404)
    def resource_not_found(e):
        return jsonify({"error": "Requested resource was not found."}), 404

    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "An internal server error occurred.",
            "message": str(e)
        }), 500

    # 10. Register CLI command: flask reconcile
    @app.cli.command("reconcile")
    def reconcile_command():
        """Runs the financial ledger reconciliation audit."""
        from app.services.reconciliation_service import reconcile_system_balances
        report = reconcile_system_balances(db.session)
        click.echo("==================================================")
        click.echo("           BANKFLOW FINANCIAL RECONCILIATION      ")
        click.echo("==================================================")
        click.echo(f"Status:                      {report['status']}")
        click.echo(f"Total Accounts:              {report['accounts_count']}")
        click.echo(f"Total Account Balances:      ${report['total_account_balances']}")
        click.echo(f"Total Ledger Credits:        ${report['total_ledger_credits']}")
        click.echo(f"Total Ledger Debits:         ${report['total_ledger_debits']}")
        click.echo(f"Completed Transactions:      {report['total_completed_transactions']}")
        click.echo(f"Discrepancies:               {report['transfer_discrepancies_count']}")
        click.echo("==================================================")

    # 11. Auto-create database tables & ensure demo accounts
    with app.app_context():
        try:
            db.create_all()
            from app.services.auth_service import ensure_demo_accounts
            ensure_demo_accounts()
        except Exception:
            pass

    return app


# Default WSGI app instance for servers using 'gunicorn app:app'
app = create_app()
