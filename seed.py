"""
Database Seeder Script for BankFlow.
Seeds demo Customer and Admin accounts for immediate local testing, provisions Double-Entry Ledger entries, and verifies system reconciliation.
"""
from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models.domain import User, Account, UserRole, AccountStatus, LedgerEntry, LedgerEntryType
from app.services.auth_service import register_user
from app.services.reconciliation_service import reconcile_system_balances


def seed_database():
    app = create_app()
    with app.app_context():
        db.create_all()

        print("Checking existing seed users...")
        # Check if admin exists
        admin = User.query.filter_by(email="admin@bankflow.com").first()
        if not admin:
            print("Creating Admin account (admin@bankflow.com / AdminPassword123!)...")
            res = register_user(
                full_name="System Administrator",
                email="admin@bankflow.com",
                password="AdminPassword123!",
                role="ADMIN",
                initial_deposit=Decimal("10000.00")
            )
            acc_id = res["primary_account"]["account_id"]
            db.session.add(LedgerEntry(
                account_id=acc_id,
                entry_type=LedgerEntryType.CREDIT,
                amount=Decimal("10000.00"),
                balance_after=Decimal("10000.00"),
                description="Initial Admin provision balance"
            ))
            db.session.commit()

        # Check if Demo Customer 1 exists
        alice = User.query.filter_by(email="alice@example.com").first()
        if not alice:
            print("Creating Alice Customer account (alice@example.com / Password123!)...")
            res = register_user(
                full_name="Alice Johnson",
                email="alice@example.com",
                password="Password123!",
                role="CUSTOMER",
                initial_deposit=Decimal("2500.00")
            )
            acc_id = res["primary_account"]["account_id"]
            db.session.add(LedgerEntry(
                account_id=acc_id,
                entry_type=LedgerEntryType.CREDIT,
                amount=Decimal("2500.00"),
                balance_after=Decimal("2500.00"),
                description="Initial Alice deposit"
            ))
            db.session.commit()

        # Check if Demo Customer 2 exists
        bob = User.query.filter_by(email="bob@example.com").first()
        if not bob:
            print("Creating Bob Customer account (bob@example.com / Password123!)...")
            res = register_user(
                full_name="Bob Smith",
                email="bob@example.com",
                password="Password123!",
                role="CUSTOMER",
                initial_deposit=Decimal("1500.00")
            )
            acc_id = res["primary_account"]["account_id"]
            db.session.add(LedgerEntry(
                account_id=acc_id,
                entry_type=LedgerEntryType.CREDIT,
                amount=Decimal("1500.00"),
                balance_after=Decimal("1500.00"),
                description="Initial Bob deposit"
            ))
            db.session.commit()

        recon = reconcile_system_balances(db.session)
        print(f"Seeding complete! Reconciliation Status: {recon['status']} (Total Balance: ${recon['total_account_balances']})")


if __name__ == "__main__":
    seed_database()
