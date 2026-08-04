"""Shared test fixtures for the AegisFlow application skeleton."""

import asyncio
from collections.abc import AsyncIterator
import sys

import httpx
import pytest


if sys.platform == "win32":
    # psycopg's async implementation requires a selector-based loop on Windows.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture
def valid_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide the minimum valid process environment for app construction."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://aegisflow_test:aegisflow_test@localhost/aegisflow_test",
    )
    monkeypatch.delenv("APP_BASE_URL", raising=False)
    for name in (
        "GITHUB_APP_ID",
        "GITHUB_APP_PRIVATE_KEY",
        "GITHUB_APP_WEBHOOK_SECRET",
        "GITHUB_APP_INSTALLATION_ID",
        "GITHUB_API_TIMEOUT_SECONDS",
        "AEGISFLOW_BOOTSTRAP_TENANT_SLUG",
        "OIDC_ISSUER",
        "OIDC_AUDIENCE",
        "OIDC_JWKS_URL",
        "OIDC_ALGORITHM",
        "OIDC_CACHE_TTL_SECONDS",
        "OIDC_MAX_CACHED_KEYS",
        "OIDC_HTTP_TIMEOUT_SECONDS",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_SERVICE_NAME",
        "MODEL_PRIMARY_NAME",
        "MODEL_PRIMARY_API_KEY_ENV",
        "MODEL_FALLBACK_NAME",
        "MODEL_FALLBACK_API_KEY_ENV",
        "MODEL_LOCAL_FALLBACK_ENABLED",
        "MODEL_LOCAL_FALLBACK_NAME",
        "MODEL_LOCAL_FALLBACK_API_KEY_ENV",
        "MODEL_LOCAL_FALLBACK_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def anyio_backend() -> str:
    """Keep async component tests on the project's asyncio runtime."""
    return "asyncio"


@pytest.fixture
async def client(valid_env: None) -> AsyncIterator[httpx.AsyncClient]:
    """Construct a test client without allowing server exceptions to escape."""
    from aegisflow_core.app import create_app

    transport = httpx.ASGITransport(
        app=create_app(),
        raise_app_exceptions=False,
    )
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client
