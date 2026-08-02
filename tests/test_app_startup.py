"""Component tests for application construction and safe failure behavior."""

import importlib
import sys

import httpx
import pytest
from fastapi import FastAPI

from aegisflow_core.app import create_app
from aegisflow_core.settings import ConfigurationError


def test_create_app_succeeds_with_valid_env(valid_env: None) -> None:
    assert isinstance(create_app(), FastAPI)


def test_create_app_fails_fast_without_app_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)

    with pytest.raises(ConfigurationError):
        create_app()


def test_create_app_fails_fast_with_invalid_app_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "staging")

    with pytest.raises(ConfigurationError):
        create_app()


def test_main_exposes_fastapi_app(valid_env: None) -> None:
    sys.modules.pop("aegisflow_core.main", None)

    main = importlib.import_module("aegisflow_core.main")

    assert isinstance(main.app, FastAPI)


@pytest.mark.anyio
async def test_unhandled_exception_returns_structured_error(valid_env: None) -> None:
    app = create_app()

    @app.get("/_test/unhandled")
    async def raise_unhandled_error() -> None:
        raise RuntimeError("sensitive internal detail")

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get("/_test/unhandled")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "An internal error occurred.",
        }
    }
    assert "sensitive internal detail" not in response.text
    assert "Traceback" not in response.text
