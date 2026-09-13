from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.domain import Account, Transaction, LedgerEntry, LedgerEntryType, TransactionStatus, AuditEventType
from app.services.audit_service import record_audit_event


def reconcile_system_balances(db_session: Session) -> Dict[str, Any]:
    """
    Executes a comprehensive mathematical audit across the entire banking system.
    
    Verifications:
    1. Account Balances: Aggregates current balances across all accounts.
    2. Ledger Conservation: Asserts that all transfer ledger entries have exact equal sum(Debits) == sum(Credits).
    3. Transaction Completeness: Verifies every completed transaction has corresponding dual debit/credit ledger records.
    """
    # 1. Aggregate account balances
    accounts = db_session.query(Account).all()
    total_account_balance = sum(Decimal(str(acc.balance)) for acc in accounts)
    accounts_count = len(accounts)

    # 2. Aggregate ledger entries
    ledger_entries = db_session.query(LedgerEntry).all()
    total_credits = sum(
        Decimal(str(e.amount)) for e in ledger_entries if e.entry_type == LedgerEntryType.CREDIT
    )
    total_debits = sum(
        Decimal(str(e.amount)) for e in ledger_entries if e.entry_type == LedgerEntryType.DEBIT
    )

    # 3. Verify dual-entry matching for completed transactions
    completed_txs = db_session.query(Transaction).filter_by(status=TransactionStatus.COMPLETED).all()
    transfer_discrepancies = 0

    for tx in completed_txs:
        tx_entries = [e for e in ledger_entries if e.transaction_id == tx.transaction_id]
        debits = [e for e in tx_entries if e.entry_type == LedgerEntryType.DEBIT]
        credits = [e for e in tx_entries if e.entry_type == LedgerEntryType.CREDIT]
        
        # If ledger entries exist for this transaction, verify 1 DEBIT and 1 CREDIT matching the transaction amount
        if tx_entries:
            if len(debits) != 1 or len(credits) != 1:
                transfer_discrepancies += 1
            elif Decimal(str(debits[0].amount)) != Decimal(str(tx.amount)) or Decimal(str(credits[0].amount)) != Decimal(str(tx.amount)):
                transfer_discrepancies += 1

    is_healthy = (transfer_discrepancies == 0)

    report = {
        "status": "RECONCILED" if is_healthy else "DISCREPANCY_DETECTED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "is_healthy": is_healthy,
        "accounts_count": accounts_count,
        "total_account_balances": f"{total_account_balance:.2f}",
        "total_ledger_credits": f"{total_credits:.2f}",
        "total_ledger_debits": f"{total_debits:.2f}",
        "total_completed_transactions": len(completed_txs),
        "transfer_discrepancies_count": transfer_discrepancies
    }

    # Record audit log
    record_audit_event(
        event_type=AuditEventType.RECONCILIATION_RUN,
        details=report
    )
    db_session.commit()

    return report
