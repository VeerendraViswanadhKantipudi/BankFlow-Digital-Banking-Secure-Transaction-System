import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from app import create_app
from app.core.config import TestConfig
from app.extensions import db as _db, bcrypt
from app.models.domain import User, Account, Transaction, UserRole, AccountStatus, LedgerEntry, AuditLog
from app.db import validate_mysql_url


@pytest.fixture(scope="session")
def app():
    """Create and configure a Flask application instance for the test session."""
    validate_mysql_url(TestConfig.SQLALCHEMY_DATABASE_URI)
    
    app = create_app(TestConfig)
    
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="session")
def engine(app):
    """Verifies that the database engine is MySQL (InnoDB) and returns the engine."""
    eng = _db.engine
    assert eng.dialect.name == "mysql", (
        f"FATAL: Concurrency tests must run strictly against MySQL (InnoDB)! "
        f"Detected dialect: '{eng.dialect.name}'"
    )
    return eng


@pytest.fixture(scope="session")
def session_factory(engine):
    """Thread-safe sessionmaker for tests and worker threads."""
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def clean_database(app):
    """Cleans up database tables between individual tests in child-to-parent FK order."""
    yield
    with app.app_context():
        _db.session.rollback()
        _db.session.query(LedgerEntry).delete()
        _db.session.query(AuditLog).delete()
        _db.session.query(Transaction).delete()
        _db.session.query(Account).delete()
        _db.session.query(User).delete()
        _db.session.commit()


@pytest.fixture
def client(app):
    """Test client for HTTP API requests."""
    return app.test_client()


@pytest.fixture
def db_session(app):
    """Standard db session for test setups."""
    with app.app_context():
        yield _db.session
        _db.session.rollback()
