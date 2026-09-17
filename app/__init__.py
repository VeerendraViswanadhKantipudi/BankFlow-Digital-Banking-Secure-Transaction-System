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
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}}, supports_credentials=True)

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

    # 6. Global Health & Info route
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

    # 9. Global 404 and 500 handlers
    @app.errorhandler(404)
    def resource_not_found(e):
        return jsonify({"error": "Requested resource was not found."}), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return jsonify({"error": "An internal server error occurred."}), 500

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

    # 11. Auto-create database tables
    with app.app_context():
        try:
            db.create_all()
        except Exception:
            pass

    return app


# Default WSGI app instance for servers using 'gunicorn app:app'
app = create_app()
