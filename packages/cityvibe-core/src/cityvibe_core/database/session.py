"""Database session management for async operations."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from cityvibe_core.database.connection import get_engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get async session factory for creating database sessions.

    Returns:
        Configured async sessionmaker
    """
    engine = get_engine()
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for getting async database session (works outside FastAPI).

    This is the recommended way to use database sessions in standalone scripts,
    Celery tasks, or any non-FastAPI code.

    Yields:
        Async database session

    Example:
        ```python
        from cityvibe_core.database import init_db, get_session
        from cityvibe_core.models import Venue
        from sqlalchemy import select

        # Initialize database (only needed once)
        init_db()

        # Use session
        async with get_session() as session:
            result = await session.execute(select(Venue))
            venues = result.scalars().all()
        ```

    Example in Celery task:
        ```python
        from celery import shared_task
        from cityvibe_core.database import get_session

        @shared_task
        async def process_venues():
            async with get_session() as session:
                # Your database operations here
                pass
        ```
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
            logger.debug("💾 Session committed successfully")
        except Exception:
            await session.rollback()
            logger.exception("❌ Session rollback due to error")
            raise


async def get_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency function for getting async database session.

    This wraps get_session() for use with FastAPI's Depends().

    Yields:
        Async database session

    Example:
        ```python
        from fastapi import Depends
        from cityvibe_core.database.session import get_session_dependency
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy import select
        from cityvibe_core.models import Venue

        @router.get("/venues")
        async def get_venues(session: AsyncSession = Depends(get_session_dependency)):
            result = await session.execute(select(Venue))
            return result.scalars().all()
        ```
    """
    async with get_session() as session:
        yield session
