# BankFlow — Full-Stack Transactional Banking System

A production-grade, highly concurrent transactional banking system and double-entry ledger built with **Flask**, **MySQL (InnoDB)**, **Flask-SQLAlchemy**, **JWT**, and **React**.

BankFlow is engineered with a strict focus on **transactional correctness**, **deadlock freedom**, and **provable money conservation** under extreme concurrent load.

---

## Key Highlights & Architectural Guarantees

### 1. The Transfer Engine (`app/services/transfer_service.py`)
The transfer service is decoupled from the web framework and executes atomic ledger transfers with strict guarantees:
- **Idempotency Safety**: Idempotency keys are checked before acquiring locks. Identical replay requests return the existing transaction without duplicate debits; conflicting parameter reuses raise `IdempotencyKeyConflictError` (409 Conflict).
- **Deterministic Sorted Lock Ordering**: Always locks the sender and receiver accounts in **sorted numerical order** using `SELECT ... FOR UPDATE` (`with_for_update()`). In MySQL InnoDB, this eliminates circular wait dependencies, guaranteeing zero deadlocks during simultaneous bidirectional transfers (e.g., A $\rightarrow$ B and B $\rightarrow$ A executing concurrently).
- **Atomic Double-Entry State Machine**: Transfers transition from `PENDING` $\rightarrow$ atomic balance mutations $\rightarrow$ `COMPLETED` within a single database transaction. Any failure triggers a complete rollback.
- **Strict Domain Exception Hierarchy**: The engine raises pure domain exceptions (`InsufficientBalanceError`, `AccountNotFoundError`, `AccountInactiveError`, `InvalidTransferError`, `IdempotencyKeyConflictError`) mapped cleanly to HTTP status codes in the route layer.

### 2. Security & Defense Hardening
- **MySQL (InnoDB)-Only Enforcement (`app/db.py`)**: SQLite does not support true row-level locking (`SELECT ... FOR UPDATE`). BankFlow enforces a hard startup guard that immediately rejects SQLite and non-MySQL connection strings, preventing silent fallback.
- **Strict Role Isolation & RBAC**: Public user registration (`POST /api/v1/auth/register`) strictly assigns the `CUSTOMER` role. Role self-assignment by clients is completely disallowed. Existing administrators can promote/demote user roles via `PATCH /api/v1/accounts/admin/users/<id>/role`.
- **Configured CORS Enforcement**: `app/__init__.py` enforces the exact whitelist origins configured in `CORS_ORIGINS` rather than a wildcard `*`.
- **Account Enumeration Defense**: Account lookup endpoints return a uniform `404 Not Found` whether an account ID does not exist or exists but belongs to another user (non-admin). Never returns `403` for non-owned accounts to prevent resource enumeration.
- **Timing-Safe Authentication**: The login handler executes a bcrypt comparison against a dummy hash when an email does not exist, equalizing server response time and mitigating user enumeration attacks via timing discrepancies.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, Vite, Lucide Icons, Custom CSS Design System |
| **Backend** | Python 3.10+ / Flask 3.1, Flask-SQLAlchemy 3.1, Flask-JWT-Extended, PyMySQL |
| **Database** | MySQL 8.0.16+ (InnoDB engine required for row-level locking and CHECK constraints) |
| **Testing** | Pytest + `concurrent.futures.ThreadPoolExecutor` |
| **Production Server** | Gunicorn (Multi-worker / Multi-thread) |

---

## Concurrency Test Suite Centerpiece (`tests/test_concurrency.py`)

BankFlow includes automated concurrency tests executed directly against MySQL (InnoDB):

1. **Race Condition & Overdraft Prevention (`test_concurrency_race_condition_overdraft_prevention`)**:
   - Seeds Account A with $1,000.00 and Account B with $0.00.
   - Fires 20 concurrent transfer workers requesting $100.00 each ($2,000.00 total requested).
   - Asserts: Exactly 10 transfers succeed, exactly 10 fail with `InsufficientBalanceError`, Account A balance equals $0.00, and total money is strictly conserved ($1,000.00).
2. **Deadlock Prevention & Conservation (`test_concurrency_deadlock_prevention_and_conservation`)**:
   - Seeds Account A ($1,000.00) and Account B ($1,000.00).
   - Fires 30 simultaneous transfers (15 from A $\rightarrow$ B and 15 from B $\rightarrow$ A).
   - Asserts: Zero deadlocks occur in MySQL InnoDB, no threads hang, all transfers complete, and the sum of balances before ($2,000.00) equals the sum of balances after ($2,000.00).
3. **Multi-Account Contention Mesh (`test_concurrency_multi_account_mesh_conservation`)**:
   - Seeds 4 accounts and executes 40 concurrent cross-account transfers. Asserts total system balance is 100% conserved.

---

## Project Structure

```
bankflow/
├── app/
│   ├── __init__.py              # Flask app factory, blueprint registration, strict CORS, error handlers
│   ├── extensions.py            # db (SQLAlchemy), jwt, bcrypt instances
│   ├── models/
│   │   ├── __init__.py
│   │   └── domain.py            # User, Account, Transaction models & enum definitions
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth_schema.py       # Register (role stripped) & Login schemas
│   │   ├── account_schema.py    # Account creation, deposit, status & role update schemas
│   │   └── transfer_schema.py   # Transfer request & history filter schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py      # Registration, timing-safe authentication
│   │   └── transfer_service.py  # Atomic transfer engine with deterministic lock ordering
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth_routes.py       # /api/v1/auth endpoints
│   │   ├── account_routes.py    # /api/v1/accounts endpoints (uniform 404 & admin promotion)
│   │   └── transfer_routes.py   # /api/v1/transfers endpoints (transfer + history)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # MySQL database URLs & CORS configuration
│   │   └── exceptions.py        # Pure domain exception hierarchy
│   └── db.py                    # MySQL (InnoDB)-only engine verification
├── tests/
│   ├── conftest.py              # Pytest fixtures, test DB setup & teardown
│   ├── test_auth.py             # Auth, role-stripping & timing-safe tests
│   ├── test_accounts.py         # Account CRUD, enumeration defense & admin promotion tests
│   ├── test_transfers.py        # HTTP transfer & idempotency tests
│   └── test_concurrency.py      # Multi-threaded overdraft & deadlock test suite (MySQL dialect)
├── frontend/                    # Modern React client with Concurrency Lab
├── seed.py                      # Database seeding script
├── run.py                       # Backend server entry point
├── render.yaml                  # Render deployment configuration
├── Procfile                     # Gunicorn production process definition
└── requirements.txt             # Pinned backend dependencies
```

---

## Local Setup & Quickstart

### 1. Prerequisites
- Python 3.10+
- MySQL Server 8.0.16+ (InnoDB Engine)
- Node.js 18+ and npm

### 2. Database Setup
Create the development and test databases in MySQL:
```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS bankflow; CREATE DATABASE IF NOT EXISTS bankflow_test;"
```

### 3. Backend Setup
```bash
# Install backend dependencies
pip install -r requirements.txt

# Configure environment variables (optional: create .env from .env.example)
export DATABASE_URL="mysql+pymysql://root:password@localhost:3306/bankflow"
export TEST_DATABASE_URL="mysql+pymysql://root:password@localhost:3306/bankflow_test"
export SECRET_KEY="your-secret-key"
export JWT_SECRET_KEY="your-jwt-secret-key"
export CORS_ORIGINS="http://localhost:5173,http://localhost:3000"

# Seed demo users & accounts
python seed.py

# Start Flask backend server
python run.py
```
Backend API will start at `http://localhost:5000`.

### 4. Running the Pytest Concurrency Suite
```bash
python -m pytest -v
```

### 5. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend client will start at `http://localhost:5173`.

### Demo Credentials (Created by `seed.py`):
- **Admin**: `admin@bankflow.com` / `AdminPassword123!` (Balance: $10,000.00)
- **Customer 1**: `alice@example.com` / `Password123!` (Balance: $2,500.00)
- **Customer 2**: `bob@example.com` / `Password123!` (Balance: $1,500.00)

---

## Known Limitations

- **Idempotency Scope**: Idempotency-key deduplication is scoped to the transfer endpoint only, not generic network-level HTTP retry handling across all API verbs.
- **Account Number Generation**: Account number generation uses random selection with a unique database constraint; under theoretical extreme concurrent registration spikes, duplicate collisions rely on the database uniqueness constraint rather than distributed sequence coordination.
- **MySQL CHECK Constraint Compatibility**: `CHECK` constraints on table definitions are enforced by MySQL 8.0.16+. On older MySQL versions (pre-8.0.16), table-level CHECK constraints are parsed but ignored; in that case, the application-level invariant checks inside `execute_transfer()` still independently enforce non-negative balances and non-zero positive amounts.
- **Simulation Environment**: This is a self-contained double-entry banking ledger simulation with no external third-party payment gateway (e.g. Stripe), SMS/OTP, or inter-bank SWIFT/ACH network connectivity.
- **Transaction Ledger vs. Audit Log**: The transactions table is maintained as an append-only transactional ledger with immutable double-entry records. Database-level `UPDATE`/`DELETE` privilege revocation on MySQL users would be required for a formally certified immutable audit log.
