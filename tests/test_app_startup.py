"""Component tests for application construction and safe failure behavior."""

import importlib
import sys

import httpx
import pytest
from fastapi import FastAPI

from aegisflow_core.app import create_app
from aegisflow_core.settings import ConfigurationError


def test_create_app_succeeds_with_valid_env(valid_env: None) -> None:
    app = create_app()

    assert isinstance(app, FastAPI)
    assert app.state.github_token_provider is None
    assert app.state.github_read_client is None
    assert app.state.oidc_verifier is None


def test_create_app_registers_github_token_provider(
    valid_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_APP_ID", "123")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "private-key")
    monkeypatch.setenv("GITHUB_APP_WEBHOOK_SECRET", "webhook-secret")
    monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "456")

    app = create_app()

    assert app.state.github_token_provider is not None
    assert app.state.github_read_client is not None


@pytest.mark.anyio
async def test_create_app_registers_oidc_verifier_only_when_fully_configured(
    valid_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aegisflow_core.app import create_app

    for name, value in {
        "OIDC_ISSUER": "https://issuer.example.test",
        "OIDC_AUDIENCE": "aegisflow-dev",
        "OIDC_JWKS_URL": "https://issuer.example.test/jwks",
        "OIDC_ALGORITHM": "RS256",
    }.items():
        monkeypatch.setenv(name, value)
    app = create_app()
    assert app.state.oidc_verifier is not None
    async with app.router.lifespan_context(app):
        pass


@pytest.mark.anyio
async def test_app_lifespan_closes_owned_github_http_client(
    valid_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_APP_ID", "123")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "private-key")
    monkeypatch.setenv("GITHUB_APP_WEBHOOK_SECRET", "webhook-secret")
    monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "456")
    app = create_app()
    read_client = app.state.github_read_client

    async with app.router.lifespan_context(app):
        assert read_client._http_client.is_closed is False

    assert read_client._http_client.is_closed is True


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
