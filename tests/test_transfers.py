import pytest
from decimal import Decimal

def test_transfer_success_and_history(client):
    # Register User A (Sender)
    reg_a = client.post('/api/v1/auth/register', json={
        'full_name': 'Sender User',
        'email': 'sender@example.com',
        'password': 'Password123!',
        'initial_deposit': '1000.00'
    })
    token_a = reg_a.get_json()['data']['access_token']
    acc_a_id = reg_a.get_json()['data']['primary_account']['account_id']

    # Register User B (Receiver)
    reg_b = client.post('/api/v1/auth/register', json={
        'full_name': 'Receiver User',
        'email': 'receiver@example.com',
        'password': 'Password123!',
        'initial_deposit': '200.00'
    })
    token_b = reg_b.get_json()['data']['access_token']
    acc_b_id = reg_b.get_json()['data']['primary_account']['account_id']

    # Execute transfer of 350.00 from A to B
    res_transfer = client.post('/api/v1/transfers', json={
        'sender_account_id': acc_a_id,
        'receiver_account_id': acc_b_id,
        'amount': '350.00',
        'idempotency_key': 'tx-unique-key-001'
    }, headers={'Authorization': f'Bearer {token_a}'})

    assert res_transfer.status_code == 201
    tx_data = res_transfer.get_json()['transaction']
    assert tx_data['status'] == 'COMPLETED'
    assert tx_data['amount'] == '350.00'

    # Check updated balances
    acc_a = client.get(f'/api/v1/accounts/{acc_a_id}', headers={'Authorization': f'Bearer {token_a}'}).get_json()['account']
    acc_b = client.get(f'/api/v1/accounts/{acc_b_id}', headers={'Authorization': f'Bearer {token_b}'}).get_json()['account']
    assert acc_a['balance'] == '650.00'
    assert acc_b['balance'] == '550.00'

    # Check transaction history for Sender
    res_history_a = client.get('/api/v1/transfers/history', headers={'Authorization': f'Bearer {token_a}'})
    assert res_history_a.status_code == 200
    history_a = res_history_a.get_json()
    assert len(history_a['transactions']) == 1
    assert history_a['pagination']['total_items'] == 1


def test_transfer_self_transfer_rejection(client):
    reg = client.post('/api/v1/auth/register', json={
        'full_name': 'Self Transfer User',
        'email': 'selftx@example.com',
        'password': 'Password123!',
        'initial_deposit': '500.00'
    })
    token = reg.get_json()['data']['access_token']
    acc_id = reg.get_json()['data']['primary_account']['account_id']

    res = client.post('/api/v1/transfers', json={
        'sender_account_id': acc_id,
        'receiver_account_id': acc_id,
        'amount': '100.00'
    }, headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 400
    assert 'differ' in res.get_json()['error'].lower() or 'self-transfer' in res.get_json()['error'].lower()


def test_transfer_insufficient_funds(client):
    reg_a = client.post('/api/v1/auth/register', json={
        'full_name': 'Poor Sender',
        'email': 'poor@example.com',
        'password': 'Password123!',
        'initial_deposit': '50.00'
    })
    token_a = reg_a.get_json()['data']['access_token']
    acc_a_id = reg_a.get_json()['data']['primary_account']['account_id']

    reg_b = client.post('/api/v1/auth/register', json={
        'full_name': 'Receiver Two',
        'email': 'recv2@example.com',
        'password': 'Password123!',
        'initial_deposit': '100.00'
    })
    acc_b_id = reg_b.get_json()['data']['primary_account']['account_id']

    res = client.post('/api/v1/transfers', json={
        'sender_account_id': acc_a_id,
        'receiver_account_id': acc_b_id,
        'amount': '150.00'
    }, headers={'Authorization': f'Bearer {token_a}'})
    assert res.status_code == 400
    assert 'insufficient' in res.get_json()['error'].lower()


def test_transfer_idempotency_safe_replay_and_conflict(client):
    reg_a = client.post('/api/v1/auth/register', json={
        'full_name': 'Idempotent Sender',
        'email': 'idem_sender@example.com',
        'password': 'Password123!',
        'initial_deposit': '500.00'
    })
    token_a = reg_a.get_json()['data']['access_token']
    acc_a_id = reg_a.get_json()['data']['primary_account']['account_id']

    reg_b = client.post('/api/v1/auth/register', json={
        'full_name': 'Idempotent Receiver',
        'email': 'idem_recv@example.com',
        'password': 'Password123!',
        'initial_deposit': '100.00'
    })
    acc_b_id = reg_b.get_json()['data']['primary_account']['account_id']

    # 1. First execution
    res1 = client.post('/api/v1/transfers', json={
        'sender_account_id': acc_a_id,
        'receiver_account_id': acc_b_id,
        'amount': '100.00',
        'idempotency_key': 'idem-key-abc-123'
    }, headers={'Authorization': f'Bearer {token_a}'})
    assert res1.status_code == 201
    tx_id_1 = res1.get_json()['transaction']['transaction_id']

    # 2. Replay same request with same idempotency key -> Returns same transaction without double debit
    res2 = client.post('/api/v1/transfers', json={
        'sender_account_id': acc_a_id,
        'receiver_account_id': acc_b_id,
        'amount': '100.00',
        'idempotency_key': 'idem-key-abc-123'
    }, headers={'Authorization': f'Bearer {token_a}'})
    assert res2.status_code == 201
    assert res2.get_json()['transaction']['transaction_id'] == tx_id_1

    # Verify sender was only debited once ( -  = )
    acc_a = client.get(f'/api/v1/accounts/{acc_a_id}', headers={'Authorization': f'Bearer {token_a}'}).get_json()['account']
    assert acc_a['balance'] == '400.00'

    # 3. Request with same idempotency key but DIFFERENT amount (.00) -> 409 Conflict
    res3 = client.post('/api/v1/transfers', json={
        'sender_account_id': acc_a_id,
        'receiver_account_id': acc_b_id,
        'amount': '200.00',
        'idempotency_key': 'idem-key-abc-123'
    }, headers={'Authorization': f'Bearer {token_a}'})
    assert res3.status_code == 409
    assert 'conflict' in res3.get_json()['error'].lower()


def test_transfer_sender_ownership_defense(client):
    reg_a = client.post('/api/v1/auth/register', json={
        'full_name': 'Real Owner',
        'email': 'owner@example.com',
        'password': 'Password123!',
        'initial_deposit': '500.00'
    })
    acc_a_id = reg_a.get_json()['data']['primary_account']['account_id']

    reg_attacker = client.post('/api/v1/auth/register', json={
        'full_name': 'Attacker',
        'email': 'attacker@example.com',
        'password': 'Password123!',
        'initial_deposit': '10.00'
    })
    token_attacker = reg_attacker.get_json()['data']['access_token']
    acc_attacker_id = reg_attacker.get_json()['data']['primary_account']['account_id']

    # Attacker tries to transfer from User A's account -> MUST return 404 (Uniform Not Found defense)
    res = client.post('/api/v1/transfers', json={
        'sender_account_id': acc_a_id,
        'receiver_account_id': acc_attacker_id,
        'amount': '250.00'
    }, headers={'Authorization': f'Bearer {token_attacker}'})

    assert res.status_code == 404
    assert 'not found' in res.get_json()['error'].lower()
