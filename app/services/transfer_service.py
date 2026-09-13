from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from app.models.domain import Account, Transaction, AccountStatus, TransactionStatus, LedgerEntry, LedgerEntryType, AuditEventType
from app.services.audit_service import record_audit_event
from app.core.exceptions import (
    InsufficientBalanceError,
    AccountNotFoundError,
    AccountInactiveError,
    InvalidTransferError,
    IdempotencyKeyConflictError,
    TransferError
)


def execute_transfer(
    db_session: Session,
    sender_id: int,
    receiver_id: int,
    amount: Decimal,
    idempotency_key: Optional[str] = None
) -> Transaction:
    """
    Executes a provably atomic, deadlock-free funds transfer between two accounts with Double-Entry Ledgering.
    
    Guarantees:
    1. Idempotency safety: Replays identical requests safely, rejects conflicts.
    2. Self-transfer prevention: Strictly rejects sender == receiver.
    3. Deterministic lock ordering: Always locks accounts in sorted account_id order (SELECT FOR UPDATE).
    4. Complete validation under lock: Checks existence, ACTIVE state, and sufficient balance.
    5. Double-Entry General Ledger: Atomically records 1 DEBIT and 1 CREDIT in ledger_entries table.
    6. Atomic 2-phase ledger mutation: PENDING -> Debits/Credits -> COMPLETED with full rollback on error.
    """
    try:
        amount = Decimal(str(amount))
    except Exception:
        raise InvalidTransferError(f"Invalid transfer amount: {amount}")

    if amount <= Decimal("0.00"):
        raise InvalidTransferError("Transfer amount must be strictly greater than zero.")

    try:
        # Step 1: Idempotency Verification
        if idempotency_key:
            existing_tx = db_session.query(Transaction).filter_by(
                idempotency_key=idempotency_key
            ).first()
            if existing_tx:
                if (
                    existing_tx.sender_account_id == sender_id
                    and existing_tx.receiver_account_id == receiver_id
                    and Decimal(str(existing_tx.amount)) == amount
                ):
                    return existing_tx
                else:
                    raise IdempotencyKeyConflictError(
                        f"Idempotency key conflict: transaction with key '{idempotency_key}' exists with different parameters."
                    )

        # Step 2: Self-Transfer Prevention Guard
        if sender_id == receiver_id:
            raise InvalidTransferError("Self-transfers are not allowed. Sender and receiver account IDs must differ.")

        # Step 3: Deterministic Lock Ordering (Deadlock Prevention)
        first_id, second_id = sorted([sender_id, receiver_id])
        
        first_account = db_session.query(Account).filter_by(
            account_id=first_id
        ).with_for_update().first()
        
        second_account = db_session.query(Account).filter_by(
            account_id=second_id
        ).with_for_update().first()

        sender_account = first_account if sender_id == first_id else second_account
        receiver_account = second_account if receiver_id == second_id else first_account

        # Step 4: Validate State & Funds Under Row Lock
        if not sender_account or not receiver_account:
            raise AccountNotFoundError("One or both transfer accounts were not found.")

        if sender_account.status != AccountStatus.ACTIVE or receiver_account.status != AccountStatus.ACTIVE:
            raise AccountInactiveError(
                f"Transfer rejected: both accounts must be ACTIVE. "
                f"Sender status: {sender_account.status.value if hasattr(sender_account.status, 'value') else sender_account.status}, "
                f"Receiver status: {receiver_account.status.value if hasattr(receiver_account.status, 'value') else receiver_account.status}."
            )

        if Decimal(str(sender_account.balance)) < amount:
            raise InsufficientBalanceError(
                f"Insufficient funds: account {sender_id} has balance {sender_account.balance}, "
                f"requested transfer is {amount}."
            )

        # Step 5: Record Transaction in PENDING state
        tx = Transaction(
            sender_account_id=sender_id,
            receiver_account_id=receiver_id,
            amount=amount,
            status=TransactionStatus.PENDING,
            idempotency_key=idempotency_key
        )
        db_session.add(tx)
        db_session.flush()  # Obtain transaction_id for ledger linking

        # Step 6: Atomic Balance Mutation
        new_sender_balance = Decimal(str(sender_account.balance)) - amount
        new_receiver_balance = Decimal(str(receiver_account.balance)) + amount
        
        sender_account.balance = new_sender_balance
        receiver_account.balance = new_receiver_balance

        # Step 7: Double-Entry General Ledger Creation (1 Debit + 1 Credit)
        debit_entry = LedgerEntry(
            transaction_id=tx.transaction_id,
            account_id=sender_id,
            entry_type=LedgerEntryType.DEBIT,
            amount=amount,
            balance_after=new_sender_balance,
            description=f"Transfer to Account #{receiver_id}"
        )
        credit_entry = LedgerEntry(
            transaction_id=tx.transaction_id,
            account_id=receiver_id,
            entry_type=LedgerEntryType.CREDIT,
            amount=amount,
            balance_after=new_receiver_balance,
            description=f"Transfer from Account #{sender_id}"
        )
        db_session.add_all([debit_entry, credit_entry])

        # Step 8: Transition Transaction Status to COMPLETED
        tx.status = TransactionStatus.COMPLETED

        # Step 9: Record Audit Log
        record_audit_event(
            event_type=AuditEventType.TRANSFER_COMPLETED,
            actor_id=sender_account.user_id,
            target_account_id=receiver_id,
            details={
                "transaction_id": tx.transaction_id,
                "sender_account_id": sender_id,
                "receiver_account_id": receiver_id,
                "amount": str(amount),
                "idempotency_key": idempotency_key
            },
            db_session=db_session
        )

        # Step 10: Commit all operations as one atomic unit
        db_session.commit()
        return tx

    except Exception:
        # Step 11: Automatic Rollback on Any Exception
        db_session.rollback()
        raise
