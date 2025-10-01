"""Database session management with connection pooling."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from pathlib import Path

from src.utils.config import config


# Create database directory if it doesn't exist
def ensure_database_directory():
    """Ensure the database directory exists."""
    db_url = config.database_url
    if db_url.startswith('sqlite:///'):
        # Extract path from URL
        db_path = db_url.replace('sqlite:///', '')
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)


# Ensure directory exists
ensure_database_directory()

# Create engine with connection pooling
engine = create_engine(
    config.database_url,
    echo=config.debug,  # Log SQL queries in debug mode
    pool_pre_ping=True,  # Verify connections before use
    connect_args={'check_same_thread': False} if 'sqlite' in config.database_url else {}
)

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False  # Allow access to objects after commit
)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Provide a transactional scope for database operations.

    This context manager handles:
    - Session creation
    - Automatic commit on success
    - Automatic rollback on error
    - Session cleanup

    Usage:
        >>> from src.database.session import get_session
        >>> with get_session() as session:
        ...     trade = session.query(Trade).first()
        ...     # Changes are automatically committed

    Yields:
        Active SQLAlchemy session

    Raises:
        Any exception that occurs during database operations
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_engine():
    """Get the SQLAlchemy engine instance.

    Returns:
        SQLAlchemy Engine object

    Usage:
        >>> from src.database.session import get_engine
        >>> engine = get_engine()
        >>> # Use for raw SQL or inspection
    """
    return engine
