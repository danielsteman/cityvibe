"""Alembic environment configuration for SQLModel migrations."""

import os
import sys
from logging.config import fileConfig
from pathlib import Path
from urllib.parse import parse_qs, urlparse, urlunparse

from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from alembic import context

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv

    # Load .env file from project root (alembic/../.env)
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # python-dotenv not installed, skip loading .env
    pass

# Add the packages directory to the path so we can import cityvibe_core
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "packages", "cityvibe-core", "src")
)

# Import all models so SQLModel.metadata is populated
# Import must happen after sys.path modification
from cityvibe_core.database.connection import get_database_url
from cityvibe_core.models import (
    Event,  # noqa: F401
    Venue,  # noqa: F401
)

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate
target_metadata = SQLModel.metadata


def _get_database_url() -> str:
    """
    Get database URL from environment or config, converting to sync format.

    Returns:
        Database URL in sync format (postgresql+psycopg2://...)

    Raises:
        ValueError: If DATABASE_URL is not set or is invalid
    """
    # Check if URL is already in config (from alembic.ini)
    database_url = config.get_main_option("sqlalchemy.url")
    
    # If not in config, try to get from environment
    if not database_url:
        try:
            database_url = get_database_url()
        except ValueError as e:
            # Check if we're in offline mode (commands that don't need DB)
            if context.is_offline_mode():
                # If DATABASE_URL is not set but we're offline, return a placeholder
                # This allows alembic commands like 'history' to work without DB
                return "postgresql+psycopg2://placeholder:placeholder@localhost/placeholder"
            else:
                # For online commands, we need a real DATABASE_URL
                raise ValueError(
                    f"DATABASE_URL is required for database operations. {e}"
                ) from e
    
    # Validate that URL doesn't contain literal placeholder text (not actual values)
    placeholder_patterns = ["placeholder", "host:port", "@host:", "/database"]
    # Only check for actual placeholder text, not valid patterns like :5432/
    if any(pattern in database_url.lower() for pattern in placeholder_patterns):
        raise ValueError(
            f"Invalid DATABASE_URL: contains placeholder values. "
            f"Please set a valid DATABASE_URL in your .env file with actual values. "
            f"Format: postgresql+asyncpg://username:password@hostname:5432/database_name"
        )

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

    return database_url


# Set the SQLAlchemy URL in the config (only if not already set)
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", _get_database_url())


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
