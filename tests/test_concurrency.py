import concurrent.futures
import pytest
from decimal import Decimal
from app.models.domain import User, Account, AccountStatus
from app.services.transfer_service import execute_transfer
from app.core.exceptions import InsufficientBalanceError, TransferError


@pytest.fixture(autouse=True)
def ensure_mysql_dialect(engine):
    """Enforces that all concurrency tests run exclusively on a real MySQL (InnoDB) database."""
    dialect_name = engine.dialect.name
    if dialect_name != "mysql":
        pytest.fail(
            f"Concurrency tests aborted: Non-MySQL dialect '{dialect_name}' detected. "
            f"MySQL (InnoDB) is mandatory for row-level locking (SELECT ... FOR UPDATE) verification."
        )


def test_concurrency_race_condition_overdraft_prevention(app, session_factory, engine):
    """
    Test 1 — Race Condition & Overdraft Prevention:
    - Seed Account A with $1,000.00 balance and Account B with $0.00.
    - Fire 20 concurrent transfer requests for $100.00 each (Total requested = $2,000.00).
    - Exactly 10 transfers must succeed and exactly 10 must fail with InsufficientBalanceError.
    - Final balance of A must be exactly $0.00; B must be exactly $1,000.00.
    - Invariant: Total money conserved (A + B == $1,000.00).
    """
    initial_balance_a = Decimal("1000.00")
    initial_balance_b = Decimal("0.00")
    transfer_amount = Decimal("100.00")
    total_workers = 20
    expected_successes = int(initial_balance_a // transfer_amount)  # 10
    expected_failures = total_workers - expected_successes         # 10

    # 1. Setup seed data in main session
    setup_session = session_factory()
    try:
        user1 = User(full_name="User Alpha", email="alpha@test.com", password_hash="dummy_hash")
        user2 = User(full_name="User Beta", email="beta@test.com", password_hash="dummy_hash")
        setup_session.add_all([user1, user2])
        setup_session.flush()

        acc_a = Account(user_id=user1.user_id, account_number="BF1111111111", balance=initial_balance_a, status=AccountStatus.ACTIVE)
        acc_b = Account(user_id=user2.user_id, account_number="BF2222222222", balance=initial_balance_b, status=AccountStatus.ACTIVE)
        setup_session.add_all([acc_a, acc_b])
        setup_session.commit()

        acc_a_id = acc_a.account_id
        acc_b_id = acc_b.account_id
    finally:
        setup_session.close()

    total_money_before = initial_balance_a + initial_balance_b

    # 2. Worker function: each thread MUST create and close its OWN database session
    def transfer_worker(worker_id):
        worker_session = session_factory()
        try:
            tx = execute_transfer(
                db_session=worker_session,
                sender_id=acc_a_id,
                receiver_id=acc_b_id,
                amount=transfer_amount,
                idempotency_key=f"race-tx-{worker_id}"
            )
            return {"status": "SUCCESS", "tx_id": tx.transaction_id}
        except InsufficientBalanceError as e:
            return {"status": "INSUFFICIENT_BALANCE", "error": str(e)}
        except Exception as e:
            return {"status": "UNEXPECTED_ERROR", "error": str(e), "type": type(e).__name__}
        finally:
            worker_session.close()

    # 3. Fire concurrent transfers via ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=total_workers) as executor:
        futures = [executor.submit(transfer_worker, i) for i in range(total_workers)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # 4. Analyze results
    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    insufficient_count = sum(1 for r in results if r["status"] == "INSUFFICIENT_BALANCE")
    unexpected_errors = [r for r in results if r["status"] == "UNEXPECTED_ERROR"]

    assert len(unexpected_errors) == 0, f"Unexpected errors encountered: {unexpected_errors}"
    assert success_count == expected_successes, (
        f"Expected {expected_successes} transfers to succeed, but {success_count} succeeded."
    )
    assert insufficient_count == expected_failures, (
        f"Expected {expected_failures} transfers to fail with InsufficientBalanceError, but {insufficient_count} failed."
    )

    # 5. Verify final balances and money conservation invariant
    verify_session = session_factory()
    try:
        final_acc_a = verify_session.query(Account).filter_by(account_id=acc_a_id).one()
        final_acc_b = verify_session.query(Account).filter_by(account_id=acc_b_id).one()

        assert Decimal(str(final_acc_a.balance)) == Decimal("0.00"), (
            f"Account A balance should be 0.00, got {final_acc_a.balance}"
        )
        assert Decimal(str(final_acc_b.balance)) == Decimal("1000.00"), (
            f"Account B balance should be 1000.00, got {final_acc_b.balance}"
        )

        total_money_after = Decimal(str(final_acc_a.balance)) + Decimal(str(final_acc_b.balance))
        assert total_money_after == total_money_before, (
            f"MONEY CONSERVATION VIOLATION: Before = {total_money_before}, After = {total_money_after}"
        )
    finally:
        verify_session.close()


def test_concurrency_deadlock_prevention_and_conservation(app, session_factory, engine):
    """
    Test 2 — Deadlock Prevention & Money Conservation:
    - Seed Account A with $1,000.00 and Account B with $1,000.00.
    - Fire 30 concurrent transfer requests:
      - 15 transfers A -> B ($20.00 each)
      - 15 transfers B -> A ($20.00 each)
    - Deterministic lock ordering (locking by sorted account_id) ensures zero deadlocks in MySQL InnoDB.
    - Invariant: Zero deadlocks / hangs, all 30 complete, and total money is strictly conserved.
    """
    initial_balance_a = Decimal("1000.00")
    initial_balance_b = Decimal("1000.00")
    transfer_amount = Decimal("20.00")
    transfers_per_direction = 15
    total_transfers = transfers_per_direction * 2

    # 1. Setup seed data in main session
    setup_session = session_factory()
    try:
        user1 = User(full_name="User Delta", email="delta@test.com", password_hash="dummy_hash")
        user2 = User(full_name="User Gamma", email="gamma@test.com", password_hash="dummy_hash")
        setup_session.add_all([user1, user2])
        setup_session.flush()

        acc_a = Account(user_id=user1.user_id, account_number="BF3333333333", balance=initial_balance_a, status=AccountStatus.ACTIVE)
        acc_b = Account(user_id=user2.user_id, account_number="BF4444444444", balance=initial_balance_b, status=AccountStatus.ACTIVE)
        setup_session.add_all([acc_a, acc_b])
        setup_session.commit()

        acc_a_id = acc_a.account_id
        acc_b_id = acc_b.account_id
    finally:
        setup_session.close()

    total_money_before = initial_balance_a + initial_balance_b

    # 2. Worker function with its own session per thread
    def bidirectional_worker(direction, idx):
        worker_session = session_factory()
        try:
            if direction == "A_TO_B":
                sender, receiver = acc_a_id, acc_b_id
            else:
                sender, receiver = acc_b_id, acc_a_id

            tx = execute_transfer(
                db_session=worker_session,
                sender_id=sender,
                receiver_id=receiver,
                amount=transfer_amount,
                idempotency_key=f"bidirect-{direction}-{idx}"
            )
            return {"status": "SUCCESS", "tx_id": tx.transaction_id, "direction": direction}
        except Exception as e:
            return {"status": "ERROR", "error": str(e), "type": type(e).__name__, "direction": direction}
        finally:
            worker_session.close()

    # 3. Fire all 30 bidirectional transfers simultaneously
    tasks = []
    for i in range(transfers_per_direction):
        tasks.append(("A_TO_B", i))
        tasks.append(("B_TO_A", i))

    with concurrent.futures.ThreadPoolExecutor(max_workers=total_transfers) as executor:
        futures = [executor.submit(bidirectional_worker, direction, idx) for direction, idx in tasks]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # 4. Assertions: Zero failures or deadlocks
    errors = [r for r in results if r["status"] == "ERROR"]
    assert len(errors) == 0, f"Deadlock or error occurred during concurrent execution: {errors}"
    assert len(results) == total_transfers, f"Expected {total_transfers} results, got {len(results)}"

    # 5. Assert final balances and money conservation
    verify_session = session_factory()
    try:
        final_acc_a = verify_session.query(Account).filter_by(account_id=acc_a_id).one()
        final_acc_b = verify_session.query(Account).filter_by(account_id=acc_b_id).one()

        assert Decimal(str(final_acc_a.balance)) == initial_balance_a
        assert Decimal(str(final_acc_b.balance)) == initial_balance_b

        total_money_after = Decimal(str(final_acc_a.balance)) + Decimal(str(final_acc_b.balance))
        assert total_money_after == total_money_before, (
            f"MONEY CONSERVATION VIOLATION: Total before = {total_money_before}, Total after = {total_money_after}"
        )
    finally:
        verify_session.close()


def test_concurrency_multi_account_mesh_conservation(app, session_factory, engine):
    """
    Test 3 — Multi-Account Mesh Contention & Money Conservation:
    - 4 Accounts (A, B, C, D) seeded with $500.00 each ($2,000.00 total).
    - 40 concurrent transfers randomly routing between accounts.
    - Proves money is strictly conserved across a complex transaction mesh.
    """
    account_count = 4
    initial_balance_each = Decimal("500.00")
    total_money_before = initial_balance_each * account_count

    setup_session = session_factory()
    account_ids = []
    try:
        user = User(full_name="Mesh User", email="mesh@test.com", password_hash="dummy_hash")
        setup_session.add(user)
        setup_session.flush()

        for i in range(account_count):
            acc = Account(
                user_id=user.user_id,
                account_number=f"BF999999990{i}",
                balance=initial_balance_each,
                status=AccountStatus.ACTIVE
            )
            setup_session.add(acc)
            setup_session.flush()
            account_ids.append(acc.account_id)
        setup_session.commit()
    finally:
        setup_session.close()

    transfers = [
        (account_ids[0], account_ids[1], Decimal("50.00")),
        (account_ids[1], account_ids[2], Decimal("30.00")),
        (account_ids[2], account_ids[3], Decimal("40.00")),
        (account_ids[3], account_ids[0], Decimal("20.00")),
        (account_ids[1], account_ids[0], Decimal("25.00")),
        (account_ids[2], account_ids[0], Decimal("15.00")),
        (account_ids[3], account_ids[1], Decimal("35.00")),
        (account_ids[0], account_ids[2], Decimal("45.00")),
    ] * 5  # 40 transfers in total

    def mesh_worker(sender, receiver, amount, idx):
        worker_session = session_factory()
        try:
            execute_transfer(
                db_session=worker_session,
                sender_id=sender,
                receiver_id=receiver,
                amount=amount,
                idempotency_key=f"mesh-tx-{idx}"
            )
            return True
        finally:
            worker_session.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(mesh_worker, s, r, a, i) for i, (s, r, a) in enumerate(transfers)]
        [f.result() for f in concurrent.futures.as_completed(futures)]

    # Verify money conservation invariant
    verify_session = session_factory()
    try:
        accounts = verify_session.query(Account).filter(Account.account_id.in_(account_ids)).all()
        total_money_after = sum(Decimal(str(acc.balance)) for acc in accounts)
        
        for acc in accounts:
            assert Decimal(str(acc.balance)) >= Decimal("0.00"), f"Account {acc.account_id} balance is negative: {acc.balance}"

        assert total_money_after == total_money_before, (
            f"MESH MONEY CONSERVATION VIOLATION: Expected {total_money_before}, Got {total_money_after}"
        )
    finally:
        verify_session.close()
