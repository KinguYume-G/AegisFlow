"""PostgreSQL fixtures for AF-103 integration tests."""

from collections.abc import AsyncIterator
import os

import pytest
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine


@pytest.fixture
async def db_connection() -> AsyncIterator[AsyncConnection]:
    """Run each database test in a rollback-only transaction."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for PostgreSQL integration tests")

    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield connection
        finally:
            if transaction.is_active:
                await transaction.rollback()
    await engine.dispose()
