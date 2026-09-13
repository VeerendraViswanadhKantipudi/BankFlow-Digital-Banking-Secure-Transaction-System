import pytest
from app.models.domain import User, Account

def test_register_success(client):
    res = client.post('/api/v1/auth/register', json={
        'full_name': 'Alice Smith',
        'email': 'alice@example.com',
        'password': 'Password123!',
        'initial_deposit': '500.00'
    })
    assert res.status_code == 201
    data = res.get_json()['data']
    assert data['user']['email'] == 'alice@example.com'
    assert data['user']['full_name'] == 'Alice Smith'
    assert data['user']['role'] == 'CUSTOMER'
    assert 'access_token' in data
    assert data['primary_account']['balance'] == '500.00'
    assert data['primary_account']['account_number'].startswith('BF')


def test_register_ignores_client_supplied_role(client):
    """Assert that passing role=ADMIN in registration is ignored and the user gets CUSTOMER."""
    res = client.post('/api/v1/auth/register', json={
        'full_name': 'Eve Sneaky',
        'email': 'eve_attacker@example.com',
        'password': 'Password123!',
        'role': 'ADMIN'
    })
    assert res.status_code == 201
    data = res.get_json()['data']
    assert data['user']['role'] == 'CUSTOMER', "Security failure: registration allowed public ADMIN self-assignment!"


def test_register_duplicate_email(client):
    client.post('/api/v1/auth/register', json={
        'full_name': 'Alice Smith',
        'email': 'duplicate@example.com',
        'password': 'Password123!'
    })
    res = client.post('/api/v1/auth/register', json={
        'full_name': 'Another Alice',
        'email': 'duplicate@example.com',
        'password': 'Password123!'
    })
    assert res.status_code == 400
    assert 'already exists' in res.get_json()['error']


def test_login_success(client):
    client.post('/api/v1/auth/register', json={
        'full_name': 'Bob Jones',
        'email': 'bob@example.com',
        'password': 'SecretPassword123!'
    })

    res = client.post('/api/v1/auth/login', json={
        'email': 'bob@example.com',
        'password': 'SecretPassword123!'
    })
    assert res.status_code == 200
    data = res.get_json()['data']
    assert 'access_token' in data
    assert data['user']['email'] == 'bob@example.com'


def test_login_invalid_password(client):
    client.post('/api/v1/auth/register', json={
        'full_name': 'Bob Jones',
        'email': 'bob2@example.com',
        'password': 'SecretPassword123!'
    })

    res = client.post('/api/v1/auth/login', json={
        'email': 'bob2@example.com',
        'password': 'WrongPassword!'
    })
    assert res.status_code == 401
    assert 'Invalid email or password' in res.get_json()['error']


def test_login_nonexistent_user_timing_safe(client):
    res = client.post('/api/v1/auth/login', json={
        'email': 'nonexistent@example.com',
        'password': 'SomePassword123!'
    })
    assert res.status_code == 401
    assert 'Invalid email or password' in res.get_json()['error']


def test_get_current_user_me(client):
    reg = client.post('/api/v1/auth/register', json={
        'full_name': 'Charlie Day',
        'email': 'charlie@example.com',
        'password': 'Password123!'
    })
    token = reg.get_json()['data']['access_token']

    res = client.get('/api/v1/auth/me', headers={
        'Authorization': f'Bearer {token}'
    })
    assert res.status_code == 200
    user_data = res.get_json()['user']
    assert user_data['email'] == 'charlie@example.com'
    assert len(user_data['accounts']) == 1
