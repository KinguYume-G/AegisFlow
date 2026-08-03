"""Short-lived GitHub App installation-token acquisition."""

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

import httpx
import jwt
from pydantic import BaseModel, ConfigDict, field_validator

from aegisflow_core.packs.delivery.contracts.determinism import Clock


class InstallationToken(BaseModel):
    """A cached GitHub installation token and its absolute expiry."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    token: str
    expires_at: datetime

    @field_validator("expires_at")
    @classmethod
    def expiry_must_be_utc_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("expires_at must be a timezone-aware UTC datetime")
        return value


class GitHubAppAuthError(RuntimeError):
    """Safe public error for GitHub App authentication failures."""


class _Response(Protocol):
    def raise_for_status(self) -> None: ...
    def json(self) -> dict[str, Any]: ...


class _HttpClient(Protocol):
    async def post(self, url: str, **kwargs: Any) -> _Response: ...


JwtEncoder = Callable[..., str]


class InstallationTokenProvider:
    """Create, cache, and safely refresh one installation token."""

    _REFRESH_BUFFER = timedelta(seconds=60)

    def __init__(
        self,
        *,
        app_id: str,
        private_key_pem: str,
        installation_id: str,
        clock: Clock,
        http_client: _HttpClient | None = None,
        jwt_encoder: JwtEncoder = jwt.encode,
        api_base_url: str = "https://api.github.com",
    ) -> None:
        self._app_id = app_id
        self._private_key_pem = private_key_pem
        self._installation_id = installation_id
        self._clock = clock
        self._http_client = http_client
        self._jwt_encoder = jwt_encoder
        self._token_url = (
            f"{api_base_url.rstrip('/')}/app/installations/"
            f"{installation_id}/access_tokens"
        )
        self._cached: InstallationToken | None = None
        self._lock = asyncio.Lock()

    async def get_token(self) -> InstallationToken:
        """Return a cached token or atomically refresh it near expiry."""
        async with self._lock:
            now = self._clock.now()
            if (
                self._cached is not None
                and self._cached.expires_at > now + self._REFRESH_BUFFER
            ):
                return self._cached

            try:
                app_jwt = self._jwt_encoder(
                    {
                        "iat": int((now - timedelta(seconds=60)).timestamp()),
                        "exp": int((now + timedelta(minutes=9)).timestamp()),
                        "iss": self._app_id,
                    },
                    self._private_key_pem,
                    algorithm="RS256",
                )
                response = await self._post(
                    headers={
                        "Accept": "application/vnd.github+json",
                        "Authorization": f"Bearer {app_jwt}",
                        "X-GitHub-Api-Version": "2022-11-28",
                    }
                )
                response.raise_for_status()
                payload = response.json()
                token = InstallationToken(
                    token=str(payload["token"]),
                    expires_at=_parse_github_datetime(str(payload["expires_at"])),
                )
            except Exception:
                raise GitHubAppAuthError(
                    "GitHub installation token request failed"
                ) from None

            self._cached = token
            return token

    async def _post(self, *, headers: dict[str, str]) -> _Response:
        if self._http_client is not None:
            return await self._http_client.post(self._token_url, headers=headers)
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.post(self._token_url, headers=headers)


def _parse_github_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc)
