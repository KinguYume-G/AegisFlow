"""Async SQLAlchemy engine and session construction."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from aegisflow_core.settings import Settings, get_settings


def create_database_engine(settings: Settings | None = None) -> AsyncEngine:
    """Create an async engine without opening a database connection."""
    resolved_settings = settings or get_settings()
    return create_async_engine(
        resolved_settings.database_url,
        pool_pre_ping=True,
    )


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create the shared async session factory for a configured engine."""
    return async_sessionmaker(engine, expire_on_commit=False)
