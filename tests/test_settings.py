"""Unit tests for minimal process-environment configuration."""

import pytest

from aegisflow_core.settings import ConfigurationError, get_settings


@pytest.mark.parametrize("app_env", ["development", "test", "production"])
def test_valid_app_env_accepted(
    monkeypatch: pytest.MonkeyPatch, app_env: str
) -> None:
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.delenv("APP_BASE_URL", raising=False)

    settings = get_settings()

    assert settings.app_env == app_env
    assert settings.app_base_url is None


def test_missing_app_env_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)

    with pytest.raises(ConfigurationError):
        get_settings()


def test_invalid_app_env_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")

    with pytest.raises(ConfigurationError):
        get_settings()


def test_app_base_url_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_BASE_URL", "https://aegisflow.example.test")

    settings = get_settings()

    assert settings.app_base_url == "https://aegisflow.example.test"
