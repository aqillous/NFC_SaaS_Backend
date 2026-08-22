"""
Database engine and session management (SQLAlchemy 2.x).
"""
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Supabase (and most hosted Postgres) requires SSL. Passing sslmode=require
# here means you don't have to remember to append it to DATABASE_URL yourself.
connect_args = {}
if settings.DATABASE_URL.startswith("postgresql"):
    connect_args["sslmode"] = "require" if settings.DB_SSL_REQUIRE else "prefer"

# If we're going through Supabase's pgbouncer connection pooler (port 6543,
# "Transaction" mode), pgbouncer already pools connections for us — layering
# SQLAlchemy's own pool on top of it just wastes connections and can cause
# "prepared statement already exists" style issues under load. In that case
# we disable SQLAlchemy's pool (NullPool) and let pgbouncer do the pooling.
# For a direct connection (port 5432) or the Session pooler, SQLAlchemy's
# normal QueuePool (the default) is what we want.
using_transaction_pooler = ":6543" in settings.DATABASE_URL

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # avoids stale-connection errors after DB restarts / idle timeouts
    connect_args=connect_args,
    poolclass=NullPool if using_transaction_pooler else None,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def get_db() -> Generator:
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
