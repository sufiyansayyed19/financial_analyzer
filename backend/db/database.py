"""
🧠 FinRAG — Database Connection
==================================

WHAT THIS DOES:
---------------
Creates and manages the database connection.

WHY A SEPARATE FILE?
---------------------
Database connection setup is INFRASTRUCTURE — it doesn't contain
business logic. Keeping it separate means:
  - models.py defines WHAT we store (tables, columns)
  - database.py handles HOW we connect (engine, sessions)
  - Pipeline code just uses sessions without caring about setup

KEY CONCEPTS:
--------------
1. ENGINE: The connection pool to the database.
   Think of it as a "phone line" to the database.

2. SESSION: A conversation over that phone line.
   Each request/operation gets its own session.
   When done, the session is closed (like hanging up).

3. BASE: The parent class for all our models.
   SQLAlchemy uses this to track which tables exist.

WHAT YOU'LL LEARN:
- SQLAlchemy engine and session patterns
- Why we use a session factory
- How the same code works on SQLite AND PostgreSQL
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.core.config import settings
from backend.core.logging import get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# 🏗 DECLARATIVE BASE
# ──────────────────────────────────────────────
# All our models (tables) inherit from this.
# SQLAlchemy uses it to track all registered tables
# and create them in init_db().

class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# ──────────────────────────────────────────────
# ⚙️ ENGINE CREATION
# ──────────────────────────────────────────────
# The engine manages the actual database connection.
#
# For SQLite: creates/opens a file called finrag.db
# For PostgreSQL: connects to the running server
#
# connect_args={"check_same_thread": False}
#   → SQLite-specific: allows multiple threads to share one connection
#   → Not needed for PostgreSQL (it handles threads natively)

def _create_engine():
    """Create the database engine from settings."""
    connect_args = {}

    # SQLite needs special handling for multi-threaded access
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(
        settings.database_url,
        connect_args=connect_args,
        # echo=True would print every SQL query — useful for debugging
        echo=False,
    )

    # Enable WAL mode for SQLite (better concurrent read/write performance)
    if settings.database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = _create_engine()


# ──────────────────────────────────────────────
# 🔄 SESSION FACTORY
# ──────────────────────────────────────────────
# A session is a "workspace" for database operations.
#
# WHY A FACTORY?
# Each operation (API request, pipeline step) should get
# its own session. A factory creates fresh sessions on demand.
#
# PATTERN:
#   with get_session() as session:
#       session.add(some_object)
#       session.commit()
#   # Session is automatically closed here

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session():
    """
    Get a database session.

    Usage:
        session = get_session()
        try:
            session.add(obj)
            session.commit()
        finally:
            session.close()
    """
    return SessionLocal()


# ──────────────────────────────────────────────
# 🚀 DATABASE INITIALIZATION
# ──────────────────────────────────────────────

def init_db():
    """
    Create all database tables.

    This is IDEMPOTENT — running it multiple times won't
    duplicate or destroy existing tables. It only creates
    tables that don't exist yet.

    HOW IT WORKS:
    Base.metadata contains info about all models that inherit from Base.
    create_all() generates the CREATE TABLE SQL for each model
    and executes it (with IF NOT EXISTS).
    """
    # Import models so they register with Base.metadata
    import backend.db.models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Log which database we're using
    if settings.database_url.startswith("sqlite"):
        db_type = "SQLite"
        db_path = settings.database_url.replace("sqlite:///", "")
    else:
        db_type = "PostgreSQL"
        db_path = settings.database_url.split("@")[-1] if "@" in settings.database_url else "..."

    logger.info(f"✅ Database initialized ({db_type}: {db_path})")


# ──────────────────────────────────────────────
# 🧪 TEST: Run directly to verify database setup
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 DATABASE CONNECTION TEST")
    print("=" * 60)

    init_db()

    # Test session
    session = get_session()
    print(f"\n✅ Session created successfully")
    print(f"   Database URL: {settings.database_url}")
    session.close()
    print(f"   Session closed")
