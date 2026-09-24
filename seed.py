"""
Database Seeder Script for BankFlow (Local Development & Testing).
Provisions demo customer and administrative accounts with Double-Entry Ledger entries.
"""
import os
import sys
import argparse
import secrets
from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models.domain import User, Account, UserRole, AccountStatus, LedgerEntry, LedgerEntryType
from app.services.auth_service import register_user
from app.services.reconciliation_service import reconcile_system_balances


def parse_args():
    parser = argparse.ArgumentParser(description="Seed the BankFlow database for local development.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force execution even if running in a production or remote cloud environment."
    )
    return parser.parse_args()


def seed_database(force: bool = False):
    env = os.getenv("FLASK_ENV", "").lower()
    app_env = os.getenv("ENV", "").lower()
    db_url = os.getenv("DATABASE_URL", "").lower()

    is_production = (
        env == "production"
        or app_env == "production"
        or "aivencloud.com" in db_url
        or "rds.amazonaws.com" in db_url
    )

    if is_production and not force:
        print("[ABORT] Refusing to seed database in a PRODUCTION or remote cloud environment.")
        print("        Running seed.py in production could overwrite live data or create demo accounts.")
        print("        If you are certain this is intended, pass the --force flag: python seed.py --force")
        sys.exit(1)

    app = create_app()
    with app.app_context():
        db.create_all()

        print("--- BankFlow Database Seeding ---")

        # 1. Admin Account - Seed with randomly generated cryptographic password
        admin = User.query.filter_by(role=UserRole.ADMIN).first()
        if not admin:
            admin_password = secrets.token_urlsafe(16)
            admin_email = "admin@bankflow.local"
            print(f"Creating local Admin account ({admin_email})...")
            res = register_user(
                full_name="System Administrator",
                email=admin_email,
                password=admin_password,
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
            print("\n" + "=" * 60)
            print("🔑 ADMIN CREDENTIALS GENERATED (Local Development Only):")
            print(f"   Email:    {admin_email}")
            print(f"   Password: {admin_password}")
            print("   (Save this password now — it is not stored in plaintext or in any file)")
            print("=" * 60 + "\n")
        else:
            print(f"Admin account already exists ({admin.email}). Skipping admin creation.")

        # 2. Demo Customer 1 (Alice)
        alice = User.query.filter_by(email="alice@example.com").first()
        alice_password = "Password123!"
        if not alice:
            print("Creating Demo Customer 1 (alice@example.com)...")
            res = register_user(
                full_name="Alice Johnson",
                email="alice@example.com",
                password=alice_password,
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
            print(f"   Alice credentials -> Email: alice@example.com | Password: {alice_password}")
        else:
            alice.password_hash = bcrypt.generate_password_hash(alice_password).decode("utf-8")
            db.session.commit()
            print(f"Demo Customer 1 (alice@example.com) password synced to {alice_password}.")

        # 3. Demo Customer 2 (Bob)
        bob = User.query.filter_by(email="bob@example.com").first()
        bob_password = "Password123!"
        if not bob:
            print("Creating Demo Customer 2 (bob@example.com)...")
            res = register_user(
                full_name="Bob Smith",
                email="bob@example.com",
                password=bob_password,
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
            print(f"   Bob credentials   -> Email: bob@example.com | Password: {bob_password}")
        else:
            bob.password_hash = bcrypt.generate_password_hash(bob_password).decode("utf-8")
            db.session.commit()
            print(f"Demo Customer 2 (bob@example.com) password synced to {bob_password}.")

        recon = reconcile_system_balances(db.session)
        print(f"\n[OK] Seeding complete! Reconciliation Status: {recon['status']} (Total Balance: ${recon['total_account_balances']})")


if __name__ == "__main__":
    args = parse_args()
    seed_database(force=args.force)
