"""
BankConfig model — white-label branding configuration.

Single-row settings table. If no row exists, all values fall back to environment
variables, which themselves fall back to 'BankFlow' defaults.
This means zero-config deploys work out of the box; any bank can customise
entirely through env vars without touching the DB, or through the admin panel
(PATCH /api/v1/config/branding) which persists into this table.
"""
import os
from datetime import datetime, timezone
from app.extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class BankConfig(db.Model):
    """
    Single-row white-label configuration table.
    Only one row should ever exist (config_id=1). Enforced at service level.
    """
    __tablename__ = "bank_config"

    config_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Identity
    bank_name = db.Column(db.String(120), nullable=True)
    bank_tagline = db.Column(db.String(255), nullable=True)
    bank_logo_url = db.Column(db.String(512), nullable=True)

    # Colors (hex strings, e.g. "#2563eb")
    primary_color = db.Column(db.String(32), nullable=True)
    secondary_color = db.Column(db.String(32), nullable=True)
    accent_color = db.Column(db.String(32), nullable=True)

    # Contact & compliance
    support_email = db.Column(db.String(120), nullable=True)
    support_phone = db.Column(db.String(40), nullable=True)
    bank_country = db.Column(db.String(64), nullable=True)

    # Financial metadata
    currency_code = db.Column(db.String(8), nullable=True)    # e.g. "USD"
    currency_symbol = db.Column(db.String(8), nullable=True)  # e.g. "$"
    routing_number = db.Column(db.String(20), nullable=True)
    swift_code = db.Column(db.String(20), nullable=True)

    # Audit trail
    updated_at = db.Column(db.DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)

    def to_dict(self):
        """
        Returns the effective branding config, merging DB values with environment
        variable fallbacks and final hard-coded defaults.
        """
        def _v(db_val, env_key, default):
            if db_val is not None:
                return db_val
            return os.getenv(env_key, default)

        return {
            "bank_name":       _v(self.bank_name,      "BANK_NAME",           "BankFlow"),
            "bank_tagline":    _v(self.bank_tagline,   "BANK_TAGLINE",        "Double-Entry Digital Banking"),
            "bank_logo_url":   _v(self.bank_logo_url,  "BANK_LOGO_URL",       ""),
            "primary_color":   _v(self.primary_color,  "BANK_PRIMARY_COLOR",  "#2563eb"),
            "secondary_color": _v(self.secondary_color,"BANK_SECONDARY_COLOR","#1e40af"),
            "accent_color":    _v(self.accent_color,   "BANK_ACCENT_COLOR",   "#3b82f6"),
            "support_email":   _v(self.support_email,  "BANK_SUPPORT_EMAIL",  "support@bankflow.io"),
            "support_phone":   _v(self.support_phone,  "BANK_SUPPORT_PHONE",  ""),
            "bank_country":    _v(self.bank_country,   "BANK_COUNTRY",        "US"),
            "currency_code":   _v(self.currency_code,  "BANK_CURRENCY_CODE",  "USD"),
            "currency_symbol": _v(self.currency_symbol,"BANK_CURRENCY_SYMBOL","$"),
            "routing_number":  _v(self.routing_number, "BANK_ROUTING_NUMBER", ""),
            "swift_code":      _v(self.swift_code,     "BANK_SWIFT_CODE",     ""),
            "updated_at":      self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_or_create_singleton(cls):
        """Returns the single BankConfig row, creating it if absent."""
        row = cls.query.first()
        if row is None:
            row = cls()
            db.session.add(row)
            db.session.flush()
        return row

    @classmethod
    def effective_config(cls):
        """
        Returns the effective branding dict without needing a DB row.
        Falls back entirely to env vars + defaults if no DB row exists.
        """
        row = cls.query.first()
        if row:
            return row.to_dict()
        # No DB row — build from env/defaults directly
        return BankConfig().to_dict()

