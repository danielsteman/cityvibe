"""Alembic environment configuration for SQLModel migrations."""

import os
import sys
from logging.config import fileConfig
from urllib.parse import parse_qs, urlparse, urlunparse

from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from alembic import context

# Add the packages directory to the path so we can import cityvibe_core
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "packages", "cityvibe-core", "src")
)

# Import all models so SQLModel.metadata is populated
# Import must happen after sys.path modification
from cityvibe_core.database.connection import get_database_url
from cityvibe_core.models import Venue  # noqa: F401

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate
target_metadata = SQLModel.metadata

# Get database URL and convert to sync (Alembic uses sync SQLAlchemy)
database_url = get_database_url()

# Convert asyncpg URL to psycopg2 (sync) for Alembic
if "+asyncpg" in database_url:
    database_url = database_url.replace("+asyncpg", "")
    # Use psycopg2 for sync operations
    if not database_url.startswith("postgresql+psycopg2"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# Remove asyncpg-incompatible query parameters (already handled, but ensure clean)
parsed = urlparse(database_url)
if parsed.query:
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    incompatible_params = ["sslmode", "channel_binding"]
    cleaned_params = {k: v for k, v in query_params.items() if k not in incompatible_params}

    if cleaned_params:
        new_query = "&".join(
            f"{k}={v[0]}" if len(v) == 1 else f"{k}={','.join(v)}"
            for k, v in cleaned_params.items()
        )
    else:
        new_query = ""

    database_url = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        )
    )

# Set the SQLAlchemy URL in the config
config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a connection
    with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
