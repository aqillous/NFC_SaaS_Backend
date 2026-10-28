from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# Make sure `app` package is importable
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import Base

# Import every model module so Base.metadata is fully populated
# before autogenerate compares against it.
from app.models import user  # noqa: F401
from app.models import entity # noqa: F401
from app.models import subscription  # noqa: F401
from app.models import redirect_log  # noqa: F401
from app.models import feedback  # noqa: F401

# this is the Alembic Config object, which provides access to values within .ini file
config = context.config

# NOTE: we deliberately do NOT call config.set_main_option("sqlalchemy.url", ...)
# here. That writes into a configparser-backed object, and configparser treats
# "%" as interpolation syntax (e.g. %(name)s). URL-encoded passwords contain
# literal "%XX" sequences (e.g. "%21" for "!"), which crashes configparser with
# "invalid interpolation syntax". Instead we read settings.DATABASE_URL directly
# in Python and pass it straight to create_engine, bypassing configparser
# entirely for the URL.

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL without a DB connection)."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connects to the DB directly)."""
    connect_args = {}
    if settings.DATABASE_URL.startswith("postgresql"):
        connect_args["sslmode"] = "require" if settings.DB_SSL_REQUIRE else "prefer"

    connectable = create_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()