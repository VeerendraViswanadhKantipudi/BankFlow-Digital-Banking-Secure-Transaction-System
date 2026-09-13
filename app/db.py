"""
Database connection and MySQL (InnoDB)-only enforcement.
SQLite is strictly disallowed as it lacks true row-level locking (SELECT FOR UPDATE).
MySQL with InnoDB provides multi-version concurrency control (MVCC) and row-level locking.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

def validate_mysql_url(database_url: str) -> str:
    """
    Validates that the database connection string is strictly MySQL.
    Rejects SQLite, PostgreSQL, or any non-MySQL dialect immediately.
    Normalizes mysql:// to mysql+pymysql://.
    """
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set. A MySQL database URL is required.")
    
    cleaned = database_url.strip().lower()
    
    if cleaned.startswith("sqlite"):
        raise RuntimeError(
            "FATAL: SQLite is strictly disallowed in BankFlow. Real row-level locking "
            "(SELECT ... FOR UPDATE) requires MySQL (InnoDB) for transactional correctness "
            "and deadlock-free concurrency guarantees."
        )

    if cleaned.startswith("postgres://") or cleaned.startswith("postgresql://") or cleaned.startswith("postgresql+psycopg2://"):
        raise RuntimeError(
            "FATAL: PostgreSQL dialect detected. BankFlow has been migrated to MySQL (InnoDB). "
            "Please use a mysql+pymysql:// connection string."
        )
    
    if not (cleaned.startswith("mysql://") or cleaned.startswith("mysql+pymysql://") or cleaned.startswith("mysql+mysqldb://")):
        raise RuntimeError(
            f"Unsupported database dialect in DATABASE_URL: '{database_url}'. "
            "BankFlow requires MySQL (InnoDB)."
        )
    
    if database_url.startswith("mysql://"):
        database_url = database_url.replace("mysql://", "mysql+pymysql://", 1)
        
    return database_url


def create_standalone_engine(database_url: str):
    """Creates a standalone SQLAlchemy engine after verifying MySQL enforcement."""
    validated_url = validate_mysql_url(database_url)
    return create_engine(
        validated_url,
        pool_size=20,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True
    )


def create_standalone_session_factory(database_url: str):
    """Creates a scoped session factory for direct engine testing or worker threads."""
    engine = create_standalone_engine(database_url)
    return scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
