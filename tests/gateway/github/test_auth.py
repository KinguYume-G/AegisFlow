"""GitHub App installation-token provider tests."""

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from aegisflow_core.gateway.github.auth import (
    GitHubAppAuthError,
    InstallationTokenProvider,
)


class MutableClock:
    def __init__(self, instant: datetime) -> None:
        self.instant = instant

    def now(self) -> datetime:
        return self.instant


class FakeResponse:
    def __init__(self, payload: dict[str, Any], *, failure: Exception | None = None):
        self._payload = payload
        self._failure = failure

    def raise_for_status(self) -> None:
        if self._failure is not None:
            raise self._failure

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeHttpClient:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    async def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return self.responses.pop(0)


def _response(token: str, expires_at: datetime) -> FakeResponse:
    return FakeResponse(
        {"token": token, "expires_at": expires_at.isoformat().replace("+00:00", "Z")}
    )


@pytest.mark.anyio
async def test_provider_caches_and_refreshes_near_expiry() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    clock = MutableClock(now)
    client = FakeHttpClient(
        [
            _response("first-token", now + timedelta(hours=1)),
            _response("second-token", now + timedelta(hours=2)),
        ]
    )
    provider = InstallationTokenProvider(
        app_id="123",
        private_key_pem="private-key-value",
        installation_id="456",
        clock=clock,
        http_client=client,
        jwt_encoder=lambda _payload, _key, **_kwargs: "signed-app-jwt",
    )

    first = await provider.get_token()
    cached = await provider.get_token()
    clock.instant = now + timedelta(minutes=59, seconds=1)
    refreshed = await provider.get_token()

    assert first is cached
    assert refreshed.token == "second-token"
    assert len(client.calls) == 2
    assert client.calls[0]["headers"]["Authorization"] == "Bearer signed-app-jwt"


@pytest.mark.anyio
async def test_provider_error_does_not_expose_credentials() -> None:
    private_key = "highly-sensitive-private-key"
    token = "sensitive-token-value"
    client = FakeHttpClient(
        [FakeResponse({}, failure=RuntimeError(f"upstream echoed {token}"))]
    )
    provider = InstallationTokenProvider(
        app_id="123",
        private_key_pem=private_key,
        installation_id="456",
        clock=MutableClock(datetime(2026, 1, 1, tzinfo=timezone.utc)),
        http_client=client,
        jwt_encoder=lambda _payload, _key, **_kwargs: "signed-app-jwt",
    )

    with pytest.raises(GitHubAppAuthError) as caught:
        await provider.get_token()

    rendered = str(caught.value)
    assert private_key not in rendered
    assert token not in rendered
    assert caught.value.__cause__ is None
