import pytest
from decimal import Decimal
from app.services.auth_service import register_user

def test_list_accounts_and_create(client):
    reg = client.post('/api/v1/auth/register', json={
        'full_name': 'David Miller',
        'email': 'david@example.com',
        'password': 'Password123!',
        'initial_deposit': '100.00'
    })
    token = reg.get_json()['data']['access_token']
    auth_headers = {'Authorization': f'Bearer {token}'}

    # List accounts - initially 1
    res = client.get('/api/v1/accounts', headers=auth_headers)
    assert res.status_code == 200
    assert len(res.get_json()['accounts']) == 1

    # Create secondary account
    res_create = client.post('/api/v1/accounts', json={
        'initial_deposit': '250.00'
    }, headers=auth_headers)
    assert res_create.status_code == 201
    assert res_create.get_json()['account']['balance'] == '250.00'

    # List accounts again - now 2
    res_list = client.get('/api/v1/accounts', headers=auth_headers)
    assert len(res_list.get_json()['accounts']) == 2


def test_account_enumeration_defense(client):
    # User 1
    reg1 = client.post('/api/v1/auth/register', json={
        'full_name': 'User One',
        'email': 'user1@example.com',
        'password': 'Password123!',
        'initial_deposit': '100.00'
    })
    token1 = reg1.get_json()['data']['access_token']
    acc1_id = reg1.get_json()['data']['primary_account']['account_id']

    # User 2
    reg2 = client.post('/api/v1/auth/register', json={
        'full_name': 'User Two',
        'email': 'user2@example.com',
        'password': 'Password123!',
        'initial_deposit': '200.00'
    })
    token2 = reg2.get_json()['data']['access_token']
    acc2_id = reg2.get_json()['data']['primary_account']['account_id']

    # User 1 looks up own account -> 200 OK
    res_own = client.get(f'/api/v1/accounts/{acc1_id}', headers={'Authorization': f'Bearer {token1}'})
    assert res_own.status_code == 200

    # User 1 looks up User 2's account -> MUST return uniform 404 (NOT 403)
    res_other = client.get(f'/api/v1/accounts/{acc2_id}', headers={'Authorization': f'Bearer {token1}'})
    assert res_other.status_code == 404
    assert res_other.get_json()['error'] == f"Account with ID {acc2_id} not found."

    # User 1 looks up completely non-existent account 999999 -> MUST return uniform 404
    res_nonexistent = client.get('/api/v1/accounts/999999', headers={'Authorization': f'Bearer {token1}'})
    assert res_nonexistent.status_code == 404
    assert res_nonexistent.get_json()['error'] == "Account with ID 999999 not found."


def test_admin_freeze_and_unfreeze(client):
    # Create Admin via service (internal provisioning)
    admin_auth = register_user('Admin User', 'admin@bankflow.com', 'AdminPassword123!', role='ADMIN')
    admin_token = admin_auth['access_token']
    admin_headers = {'Authorization': f'Bearer {admin_token}'}

    # Register Customer
    reg_cust = client.post('/api/v1/auth/register', json={
        'full_name': 'Customer User',
        'email': 'cust@example.com',
        'password': 'Password123!'
    })
    cust_acc_id = reg_cust.get_json()['data']['primary_account']['account_id']

    # Freeze account as Admin
    res_freeze = client.patch(f'/api/v1/accounts/{cust_acc_id}/status', json={'status': 'FROZEN'}, headers=admin_headers)
    assert res_freeze.status_code == 200
    assert res_freeze.get_json()['account']['status'] == 'FROZEN'

    # Unfreeze (ACTIVE) account as Admin
    res_active = client.patch(f'/api/v1/accounts/{cust_acc_id}/status', json={'status': 'ACTIVE'}, headers=admin_headers)
    assert res_active.status_code == 200
    assert res_active.get_json()['account']['status'] == 'ACTIVE'


def test_only_admin_can_promote_users(client):
    """Assert non-admin gets 403 on role promotion, and admin can promote/demote users."""
    # Register Customer 1
    reg1 = client.post('/api/v1/auth/register', json={
        'full_name': 'Regular Customer',
        'email': 'regular@example.com',
        'password': 'Password123!'
    })
    user1_token = reg1.get_json()['data']['access_token']
    user1_id = reg1.get_json()['data']['user']['user_id']

    # Register Customer 2
    reg2 = client.post('/api/v1/auth/register', json={
        'full_name': 'Target Customer',
        'email': 'target@example.com',
        'password': 'Password123!'
    })
    user2_id = reg2.get_json()['data']['user']['user_id']

    # Customer 1 attempts to promote Customer 2 -> MUST get 403 Forbidden
    res_unauth = client.patch(
        f'/api/v1/accounts/admin/users/{user2_id}/role',
        json={'role': 'ADMIN'},
        headers={'Authorization': f'Bearer {user1_token}'}
    )
    assert res_unauth.status_code == 403
    assert 'Admin privilege required' in res_unauth.get_json()['error']

    # Create Admin via service (internal provisioning)
    admin_auth = register_user('Admin Master', 'master_admin@bankflow.com', 'AdminPass123!', role='ADMIN')
    admin_token = admin_auth['access_token']
    admin_headers = {'Authorization': f'Bearer {admin_token}'}

    # Admin promotes Customer 2 to ADMIN -> 200 OK
    res_promote = client.patch(
        f'/api/v1/accounts/admin/users/{user2_id}/role',
        json={'role': 'ADMIN'},
        headers=admin_headers
    )
    assert res_promote.status_code == 200
    assert res_promote.get_json()['user']['role'] == 'ADMIN'

    # Admin demotes Customer 2 back to CUSTOMER -> 200 OK
    res_demote = client.patch(
        f'/api/v1/accounts/admin/users/{user2_id}/role',
        json={'role': 'CUSTOMER'},
        headers=admin_headers
    )
    assert res_demote.status_code == 200
    assert res_demote.get_json()['user']['role'] == 'CUSTOMER'


def test_deposit_endpoint(client):
    reg = client.post('/api/v1/auth/register', json={
        'full_name': 'Deposit Test',
        'email': 'deposit@example.com',
        'password': 'Password123!',
        'initial_deposit': '50.00'
    })
    token = reg.get_json()['data']['access_token']
    acc_id = reg.get_json()['data']['primary_account']['account_id']

    res = client.post(f'/api/v1/accounts/{acc_id}/deposit', json={'amount': '150.00'}, headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    assert res.get_json()['account']['balance'] == '200.00'
