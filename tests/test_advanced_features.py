from decimal import Decimal
import pytest
from app.extensions import db
from app.models.domain import User, Account, Transaction, UserRole, AccountStatus, LedgerEntry, LedgerEntryType, AuditLog, AuditEventType
from app.services.transfer_service import execute_transfer
from app.services.reconciliation_service import reconcile_system_balances


def test_double_entry_ledger_on_transfer(app, db_session):
    """Verifies that every transfer creates dual balanced DEBIT and CREDIT ledger entries."""
    user1 = User(full_name="Ledger Alice", email="ledger_alice@test.com", password_hash="dummy")
    user2 = User(full_name="Ledger Bob", email="ledger_bob@test.com", password_hash="dummy")
    db_session.add_all([user1, user2])
    db_session.flush()

    acc1 = Account(user_id=user1.user_id, account_number="BF8888888881", balance=Decimal("1000.00"), status=AccountStatus.ACTIVE)
    acc2 = Account(user_id=user2.user_id, account_number="BF8888888882", balance=Decimal("500.00"), status=AccountStatus.ACTIVE)
    db_session.add_all([acc1, acc2])
    db_session.commit()

    tx = execute_transfer(
        db_session=db_session,
        sender_id=acc1.account_id,
        receiver_id=acc2.account_id,
        amount=Decimal("250.00")
    )

    ledger_entries = db_session.query(LedgerEntry).filter_by(transaction_id=tx.transaction_id).all()
    assert len(ledger_entries) == 2

    debit_entry = next(e for e in ledger_entries if e.entry_type == LedgerEntryType.DEBIT)
    credit_entry = next(e for e in ledger_entries if e.entry_type == LedgerEntryType.CREDIT)

    assert debit_entry.account_id == acc1.account_id
    assert Decimal(str(debit_entry.amount)) == Decimal("250.00")
    assert Decimal(str(debit_entry.balance_after)) == Decimal("750.00")

    assert credit_entry.account_id == acc2.account_id
    assert Decimal(str(credit_entry.amount)) == Decimal("250.00")
    assert Decimal(str(credit_entry.balance_after)) == Decimal("750.00")


def test_audit_logging_lifecycle(client, db_session):
    """Verifies that registration, login failures, and login successes create audit log records."""
    # 1. Register User
    res = client.post("/api/v1/auth/register", json={
        "full_name": "Audit Test User",
        "email": "audit_user@test.com",
        "password": "Password123!",
        "initial_deposit": "100.00"
    })
    assert res.status_code == 201

    reg_log = db_session.query(AuditLog).filter_by(event_type=AuditEventType.USER_REGISTERED).first()
    assert reg_log is not None
    assert "audit_user@test.com" in reg_log.details_json

    # 2. Failed Login Attempt
    client.post("/api/v1/auth/login", json={
        "email": "audit_user@test.com",
        "password": "WrongPassword!"
    })
    failed_log = db_session.query(AuditLog).filter_by(event_type=AuditEventType.LOGIN_FAILED).first()
    assert failed_log is not None

    # 3. Successful Login
    client.post("/api/v1/auth/login", json={
        "email": "audit_user@test.com",
        "password": "Password123!"
    })
    success_log = db_session.query(AuditLog).filter_by(event_type=AuditEventType.LOGIN_SUCCESS).first()
    assert success_log is not None


def test_reconciliation_service_report(db_session):
    """Verifies that reconciliation detects mathematical health and flags discrepancies."""
    user1 = User(full_name="Recon User 1", email="recon1@test.com", password_hash="dummy")
    user2 = User(full_name="Recon User 2", email="recon2@test.com", password_hash="dummy")
    db_session.add_all([user1, user2])
    db_session.flush()

    acc1 = Account(user_id=user1.user_id, account_number="BF7777777771", balance=Decimal("800.00"), status=AccountStatus.ACTIVE)
    acc2 = Account(user_id=user2.user_id, account_number="BF7777777772", balance=Decimal("400.00"), status=AccountStatus.ACTIVE)
    db_session.add_all([acc1, acc2])
    db_session.commit()

    # Execute valid transfer
    execute_transfer(db_session, acc1.account_id, acc2.account_id, Decimal("100.00"))

    # Run reconciliation
    report = reconcile_system_balances(db_session)
    assert report["status"] == "RECONCILED"
    assert report["is_healthy"] is True
    assert report["transfer_discrepancies_count"] == 0
    assert report["total_account_balances"] == "1200.00"


def test_request_id_tracing_header(client):
    """Verifies that API responses include an X-Request-ID header."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert "X-Request-ID" in res.headers
    assert len(res.headers["X-Request-ID"]) > 0


def test_admin_audit_logs_and_reconcile_endpoints(client, db_session):
    """Verifies admin endpoints for viewing audit logs and running live reconciliation."""
    from app.services.auth_service import register_user
    admin_auth = register_user("Admin User", "admin_recon@test.com", "AdminPass123!", role="ADMIN")
    customer_auth = register_user("Customer User", "cust_recon@test.com", "CustPass123!", role="CUSTOMER")

    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    cust_headers = {"Authorization": f"Bearer {customer_auth['access_token']}"}

    # Customer forbidden from admin endpoints
    assert client.get("/api/v1/accounts/admin/audit-logs", headers=cust_headers).status_code == 403
    assert client.get("/api/v1/accounts/admin/reconcile", headers=cust_headers).status_code == 403

    # Admin successfully accesses audit logs
    res_logs = client.get("/api/v1/accounts/admin/audit-logs", headers=admin_headers)
    assert res_logs.status_code == 200
    data = res_logs.get_json()
    assert "audit_logs" in data
    assert "pagination" in data

    # Admin successfully runs reconciliation
    res_recon = client.get("/api/v1/accounts/admin/reconcile", headers=admin_headers)
    assert res_recon.status_code == 200
    assert res_recon.get_json()["reconciliation"]["status"] == "RECONCILED"
