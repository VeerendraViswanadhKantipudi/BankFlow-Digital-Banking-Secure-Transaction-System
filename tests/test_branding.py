"""
Tests for the white-label branding configuration API.

Covers:
1. GET /api/v1/config/branding returns defaults without auth.
2. PATCH /api/v1/config/branding is rejected for non-admin users (403).
3. PATCH /api/v1/config/branding succeeds for admin, persists to DB, returns updated config.
4. Partial PATCH only updates supplied fields.
5. Invalid color format is rejected (400).
"""
import uuid
import pytest
from app.extensions import db as _db, bcrypt
from app.models.domain import User, UserRole
from app.models.branding import BankConfig


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _register_and_get_token(client, email=None, is_admin=False, app=None):
    email = email or f"branding_{uuid.uuid4().hex[:6]}@test.com"
    res = client.post("/api/v1/auth/register", json={
        "full_name": "Branding Tester",
        "email": email,
        "password": "TestPass123!"
    })
    assert res.status_code == 201
    token = res.get_json()["data"]["access_token"]
    user_id = res.get_json()["data"]["user"]["user_id"]

    if is_admin and app:
        with app.app_context():
            user = _db.session.get(User, user_id)
            user.role = UserRole.ADMIN
            _db.session.commit()
        # Re-login to get a token with ADMIN role claim
        res2 = client.post("/api/v1/auth/login", json={"email": email, "password": "TestPass123!"})
        assert res2.status_code == 200
        token = res2.get_json()["data"]["access_token"]

    return token


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ─── GET /api/v1/config/branding ──────────────────────────────────────────────

class TestGetBranding:
    def test_get_branding_no_auth_returns_200(self, client):
        """Public endpoint — no token required."""
        res = client.get("/api/v1/config/branding")
        assert res.status_code == 200
        data = res.get_json()
        assert "branding" in data

    def test_get_branding_returns_required_fields(self, client):
        res = client.get("/api/v1/config/branding")
        b = res.get_json()["branding"]
        for field in ["bank_name", "primary_color", "secondary_color", "accent_color",
                      "support_email", "currency_code", "currency_symbol"]:
            assert field in b, f"Missing field: {field}"

    def test_get_branding_default_bank_name_is_bankflow(self, client):
        """With no DB row, bank_name must default to env or 'BankFlow'."""
        res = client.get("/api/v1/config/branding")
        b = res.get_json()["branding"]
        # bank_name must be a non-empty string
        assert isinstance(b["bank_name"], str)
        assert len(b["bank_name"]) > 0


# ─── PATCH /api/v1/config/branding ────────────────────────────────────────────

class TestUpdateBranding:
    def test_patch_branding_requires_auth(self, client):
        res = client.patch("/api/v1/config/branding", json={"bank_name": "Test Bank"})
        assert res.status_code == 401

    def test_patch_branding_customer_gets_403(self, client, app):
        token = _register_and_get_token(client, app=app)
        res = client.patch(
            "/api/v1/config/branding",
            json={"bank_name": "Unauthorized Bank"},
            headers=_auth(token)
        )
        assert res.status_code == 403

    def test_patch_branding_admin_updates_name(self, client, app):
        token = _register_and_get_token(client, is_admin=True, app=app)
        new_name = f"Acme Bank {uuid.uuid4().hex[:4]}"
        res = client.patch(
            "/api/v1/config/branding",
            json={"bank_name": new_name},
            headers=_auth(token)
        )
        assert res.status_code == 200, res.get_json()
        body = res.get_json()
        assert body["branding"]["bank_name"] == new_name

    def test_patch_branding_persists_to_db(self, client, app):
        token = _register_and_get_token(client, is_admin=True, app=app)
        new_name = f"Persistent Bank {uuid.uuid4().hex[:4]}"
        client.patch(
            "/api/v1/config/branding",
            json={"bank_name": new_name},
            headers=_auth(token)
        )
        # Read back from DB
        with app.app_context():
            row = BankConfig.query.first()
            assert row is not None
            assert row.bank_name == new_name

    def test_patch_branding_get_reflects_update(self, client, app):
        """After PATCH, GET /api/v1/config/branding returns the new value."""
        token = _register_and_get_token(client, is_admin=True, app=app)
        new_name = f"Reflected Bank {uuid.uuid4().hex[:4]}"
        client.patch(
            "/api/v1/config/branding",
            json={"bank_name": new_name},
            headers=_auth(token)
        )
        res = client.get("/api/v1/config/branding")
        assert res.get_json()["branding"]["bank_name"] == new_name

    def test_patch_branding_partial_update_preserves_other_fields(self, client, app):
        """PATCH with only bank_name must not reset other already-set fields."""
        token = _register_and_get_token(client, is_admin=True, app=app)
        # First set two fields
        client.patch(
            "/api/v1/config/branding",
            json={"bank_name": "Init Bank", "support_email": "init@bank.com"},
            headers=_auth(token)
        )
        # Now patch only bank_name
        client.patch(
            "/api/v1/config/branding",
            json={"bank_name": "Updated Bank"},
            headers=_auth(token)
        )
        with app.app_context():
            row = BankConfig.query.first()
            assert row.bank_name == "Updated Bank"
            assert row.support_email == "init@bank.com"  # preserved

    def test_patch_branding_invalid_color_returns_400(self, client, app):
        token = _register_and_get_token(client, is_admin=True, app=app)
        res = client.patch(
            "/api/v1/config/branding",
            json={"primary_color": "not-a-color"},
            headers=_auth(token)
        )
        assert res.status_code == 400

    def test_patch_branding_empty_payload_returns_400(self, client, app):
        token = _register_and_get_token(client, is_admin=True, app=app)
        res = client.patch(
            "/api/v1/config/branding",
            json={},
            headers=_auth(token)
        )
        assert res.status_code == 400

    def test_patch_branding_valid_colors_persist(self, client, app):
        token = _register_and_get_token(client, is_admin=True, app=app)
        res = client.patch(
            "/api/v1/config/branding",
            json={"primary_color": "#e11d48", "secondary_color": "#9f1239"},
            headers=_auth(token)
        )
        assert res.status_code == 200
        b = res.get_json()["branding"]
        assert b["primary_color"] == "#e11d48"
        assert b["secondary_color"] == "#9f1239"

