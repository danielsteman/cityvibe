"""Database connection setup using SQLAlchemy async engine."""

import os

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def get_database_url() -> str:
    """
    Get database URL from environment variable.

    Returns:
        Database connection URL string

    Raises:
        ValueError: If DATABASE_URL environment variable is not set
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "DATABASE_URL environment variable is not set. "
            "Expected format: postgresql+asyncpg://user:password@host:port/database"
        )
    return database_url


def create_engine(database_url: str | None = None) -> AsyncEngine:
    """
    Create async SQLAlchemy engine for PostgreSQL.

    Args:
        database_url: Optional database URL. If not provided, reads from DATABASE_URL env var.

    Returns:
        Configured async SQLAlchemy engine
    """
    url = database_url or get_database_url()
    logger.info(
        f"🔗 Creating database engine for {url.split('@')[-1] if '@' in url else 'database'}"
    )

    engine = create_async_engine(
        url,
        echo=False,  # Set to True for SQL query logging
        pool_pre_ping=True,  # Verify connections before using
        pool_size=10,  # Number of connections to maintain
        max_overflow=20,  # Maximum connections beyond pool_size
    )

    return engine


# Global engine instance (initialized on first import or via init_db)
_engine: AsyncEngine | None = None


def init_db(database_url: str | None = None) -> None:
    """
    Initialize the global database engine.

    Args:
        database_url: Optional database URL. If not provided, reads from DATABASE_URL env var.
    """
    global _engine
    if _engine is None:
        _engine = create_engine(database_url)
        logger.info("✅ Database engine initialized")


def get_engine() -> AsyncEngine:
    """
    Get the global database engine, initializing it if necessary.

    Returns:
        The global async database engine

    Raises:
        RuntimeError: If engine has not been initialized
    """
    global _engine
    if _engine is None:
        init_db()
    if _engine is None:
        raise RuntimeError("Database engine failed to initialize")
    return _engine


async def close_db() -> None:
    """
    Close the global database engine and cleanup connections.
    """
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("🗑️ Database engine closed")
