"""
Tests for HTTP-level idempotency on account-create and deposit endpoints.

Covers:
1. Single-threaded replay: same Idempotency-Key returns original 200/201 without re-execution.
2. Cross-endpoint conflict: key used for deposit cannot be replayed for account-create (409).
3. No-key path: endpoints work normally without Idempotency-Key header.
4. Concurrency: simultaneous duplicate deposit requests with same key credit the account exactly once.
5. Concurrency: simultaneous duplicate account-create requests with same key create exactly one account.
"""
import uuid
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
import pytest
from app.extensions import db as _db, bcrypt
from app.models.domain import User, Account, AccountStatus, UserRole, LedgerEntry


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _register_user(client, suffix=""):
    email = f"idm_test{suffix}_{uuid.uuid4().hex[:6]}@test.com"
    res = client.post("/api/v1/auth/register", json={
        "full_name": "Idem Test",
        "email": email,
        "password": "TestPass123!"
    })
    assert res.status_code == 201, res.get_json()
    data = res.get_json()["data"]
    return data["access_token"], data["user"], data["primary_account"]


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _idem_headers(token, key):
    return {**_auth_headers(token), "Idempotency-Key": key}


# ─── Deposit Idempotency (single-threaded) ────────────────────────────────────

class TestDepositIdempotency:
    def test_deposit_no_idempotency_key_works_normally(self, client):
        token, _, acct = _register_user(client, "nodep")
        res = client.post(
            f"/api/v1/accounts/{acct['account_id']}/deposit",
            json={"amount": "100.00"},
            headers=_auth_headers(token)
        )
        assert res.status_code == 200

    def test_deposit_replay_returns_original_response_without_double_credit(self, client, app):
        token, _, acct = _register_user(client, "rep")
        key = str(uuid.uuid4())
        account_id = acct["account_id"]

        # First request
        r1 = client.post(
            f"/api/v1/accounts/{account_id}/deposit",
            json={"amount": "50.00"},
            headers=_idem_headers(token, key)
        )
        assert r1.status_code == 200
        body1 = r1.get_json()

        # Replay with same key
        r2 = client.post(
            f"/api/v1/accounts/{account_id}/deposit",
            json={"amount": "50.00"},
            headers=_idem_headers(token, key)
        )
        assert r2.status_code == 200
        body2 = r2.get_json()

        # Responses must be identical
        assert body1 == body2

        # DB must reflect exactly ONE deposit (initial balance 0 + 50 = 50)
        with app.app_context():
            acct_db = Account.query.get(account_id)
            assert Decimal(str(acct_db.balance)) == Decimal("50.00"), (
                f"Expected balance 50.00 after idempotent replay, got {acct_db.balance}"
            )

            # Ledger entries: only 1 CREDIT for the deposit (not 2)
            credits = LedgerEntry.query.filter_by(account_id=account_id).all()
            assert len(credits) == 1, (
                f"Expected 1 ledger credit for idempotent deposit, got {len(credits)}"
            )

    def test_deposit_different_keys_each_apply(self, client, app):
        token, _, acct = _register_user(client, "diff")
        account_id = acct["account_id"]

        for i in range(3):
            r = client.post(
                f"/api/v1/accounts/{account_id}/deposit",
                json={"amount": "25.00"},
                headers=_idem_headers(token, str(uuid.uuid4()))
            )
            assert r.status_code == 200

        with app.app_context():
            acct_db = Account.query.get(account_id)
            assert Decimal(str(acct_db.balance)) == Decimal("75.00"), (
                f"Expected 75.00 after 3 distinct deposits, got {acct_db.balance}"
            )

    def test_deposit_cross_endpoint_key_conflict_returns_409(self, client):
        """Same key used for deposit then for account-create must 409."""
        token, _, acct = _register_user(client, "cross")
        shared_key = str(uuid.uuid4())

        # Use key for deposit first
        r1 = client.post(
            f"/api/v1/accounts/{acct['account_id']}/deposit",
            json={"amount": "10.00"},
            headers=_idem_headers(token, shared_key)
        )
        assert r1.status_code == 200

        # Attempt to reuse same key for account creation
        r2 = client.post(
            "/api/v1/accounts",
            json={"initial_deposit": "0.00"},
            headers=_idem_headers(token, shared_key)
        )
        assert r2.status_code == 409, r2.get_json()


# ─── Account Create Idempotency (single-threaded) ────────────────────────────

class TestAccountCreateIdempotency:
    def test_create_account_replay_returns_same_account(self, client, app):
        token, user, _ = _register_user(client, "crt")
        key = str(uuid.uuid4())

        r1 = client.post(
            "/api/v1/accounts",
            json={"initial_deposit": "200.00"},
            headers=_idem_headers(token, key)
        )
        assert r1.status_code == 201
        body1 = r1.get_json()
        account_id1 = body1["account"]["account_id"]

        r2 = client.post(
            "/api/v1/accounts",
            json={"initial_deposit": "200.00"},
            headers=_idem_headers(token, key)
        )
        assert r2.status_code == 201
        body2 = r2.get_json()

        # Replayed response must refer to the SAME account
        assert body1 == body2

        # Only ONE extra account should exist beyond the primary
        with app.app_context():
            accounts = Account.query.filter_by(user_id=user["user_id"]).all()
            extra = [a for a in accounts if a.account_id != int(_primary_acct_id(client, token))]
            assert len(extra) == 1, (
                f"Expected 1 extra account after idempotent create, got {len(extra)}: "
                f"{[a.account_id for a in extra]}"
            )

    def test_create_account_without_key_still_works(self, client):
        token, _, _ = _register_user(client, "nokey")
        r = client.post(
            "/api/v1/accounts",
            json={"initial_deposit": "0.00"},
            headers=_auth_headers(token)
        )
        assert r.status_code == 201


def _primary_acct_id(client, token):
    """Helper: returns the account_id of the first account for the authenticated user."""
    res = client.get("/api/v1/accounts", headers=_auth_headers(token))
    return res.get_json()["accounts"][0]["account_id"]


# ─── Concurrency: Idempotent Deposits Under Parallel Load ────────────────────

class TestDepositIdempotencyConcurrency:
    """
    Fires N simultaneous deposit requests with the SAME Idempotency-Key.
    Exactly ONE credit must land; all responses must be 200; balance = exactly 1× amount.

    This is the concurrency-specific regression that looks correct single-threaded but
    can break under race conditions if the idempotency store write is not atomic.
    """
    N_WORKERS = 8
    DEPOSIT_AMOUNT = "100.00"

    def test_concurrent_duplicate_deposits_credit_once(self, client, app):
        token, _, acct = _register_user(client, "conc_dep")
        account_id = acct["account_id"]
        shared_key = str(uuid.uuid4())

        results = []

        def do_deposit():
            return client.post(
                f"/api/v1/accounts/{account_id}/deposit",
                json={"amount": self.DEPOSIT_AMOUNT},
                headers=_idem_headers(token, shared_key)
            )

        with ThreadPoolExecutor(max_workers=self.N_WORKERS) as pool:
            futures = [pool.submit(do_deposit) for _ in range(self.N_WORKERS)]
            for f in as_completed(futures):
                results.append(f.result())

        # All must succeed
        status_codes = [r.status_code for r in results]
        assert all(s == 200 for s in status_codes), (
            f"Expected all 200s under concurrent replay, got: {status_codes}"
        )

        # Balance must reflect exactly ONE deposit
        with app.app_context():
            acct_db = Account.query.get(account_id)
            expected = Decimal(self.DEPOSIT_AMOUNT)
            actual = Decimal(str(acct_db.balance))
            assert actual == expected, (
                f"CONCURRENCY BUG: Expected balance {expected} after {self.N_WORKERS} "
                f"concurrent idempotent deposits, got {actual} — double-credit detected!"
            )

            # Exactly 1 ledger entry
            credits = LedgerEntry.query.filter_by(account_id=account_id).all()
            assert len(credits) == 1, (
                f"CONCURRENCY BUG: Expected 1 ledger credit, got {len(credits)}"
            )


# ─── Concurrency: Idempotent Account Create Under Parallel Load ──────────────

class TestAccountCreateIdempotencyConcurrency:
    """
    Fires N simultaneous account-create requests with the SAME Idempotency-Key.
    Exactly ONE account must be created; all responses must be 201.
    """
    N_WORKERS = 8

    def test_concurrent_duplicate_account_creates_produce_one_account(self, client, app):
        token, user, primary = _register_user(client, "conc_crt")
        shared_key = str(uuid.uuid4())

        results = []

        def do_create():
            return client.post(
                "/api/v1/accounts",
                json={"initial_deposit": "0.00"},
                headers=_idem_headers(token, shared_key)
            )

        with ThreadPoolExecutor(max_workers=self.N_WORKERS) as pool:
            futures = [pool.submit(do_create) for _ in range(self.N_WORKERS)]
            for f in as_completed(futures):
                results.append(f.result())

        status_codes = [r.status_code for r in results]
        assert all(s == 201 for s in status_codes), (
            f"Expected all 201s under concurrent replay, got: {status_codes}"
        )

        # Only ONE extra account (beyond the primary provisioned at registration)
        with app.app_context():
            accounts = Account.query.filter_by(user_id=user["user_id"]).all()
            assert len(accounts) == 2, (
                f"CONCURRENCY BUG: Expected 2 accounts total (primary + 1 new), "
                f"got {len(accounts)} — duplicate account creation detected!"
            )

        # All responses must refer to the same account_id
        all_account_ids = [r.get_json()["account"]["account_id"] for r in results]
        assert len(set(all_account_ids)) == 1, (
            f"CONCURRENCY BUG: Different account IDs returned for same idempotency key: "
            f"{set(all_account_ids)}"
        )

