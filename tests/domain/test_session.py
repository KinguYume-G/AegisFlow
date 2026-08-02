"""Async SQLAlchemy session factory tests."""

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
import pytest

from aegisflow_core.control_plane.domain.session import (
    create_database_engine,
    create_session_factory,
)
from aegisflow_core.settings import Settings


@pytest.mark.anyio
async def test_engine_and_session_factory_use_approved_async_stack() -> None:
    settings = Settings(
        app_env="test",
        app_base_url=None,
        database_url="postgresql+asyncpg://user:password@localhost/database",
    )
    engine = create_database_engine(settings)
    session_factory = create_session_factory(engine)

    try:
        assert isinstance(engine, AsyncEngine)
        assert session_factory.class_ is AsyncSession
        assert engine.url.drivername == "postgresql+asyncpg"
    finally:
        await engine.dispose()
