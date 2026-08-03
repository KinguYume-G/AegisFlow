"""Fail-closed, provider-neutral OIDC bearer-token verification."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from time import monotonic
from typing import Protocol

import httpx
import jwt

_MAX_TOKEN_BYTES = 16_384
_MAX_JWKS_BYTES = 1_048_576
_ASYMMETRIC_ALGORITHMS = frozenset({"RS256", "ES256"})


class AuthenticationError(PermissionError):
    """A stable, token-free authentication rejection."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class Principal:
    issuer: str
    subject: str

    def __post_init__(self) -> None:
        if not self.issuer.strip() or not self.subject.strip():
            raise ValueError("principal issuer and subject are required")

    @property
    def actor_reference(self) -> str:
        return f"{self.issuer}|{self.subject}"


@dataclass(frozen=True, slots=True)
class OidcConfig:
    issuer: str
    audience: str
    jwks_url: str
    algorithm: str
    cache_ttl_seconds: int = 300
    max_cached_keys: int = 16
    http_timeout_seconds: float = 5.0

    def __post_init__(self) -> None:
        if not self.issuer.startswith("https://") or len(self.issuer) > 2048:
            raise ValueError("OIDC issuer must use HTTPS")
        if not self.jwks_url.startswith("https://") or len(self.jwks_url) > 2048:
            raise ValueError("OIDC JWKS URL must use HTTPS")
        if not self.audience.strip() or len(self.audience) > 255:
            raise ValueError("OIDC audience is required")
        if self.algorithm not in _ASYMMETRIC_ALGORITHMS:
            raise ValueError("OIDC algorithm must be an approved asymmetric algorithm")
        if not 1 <= self.cache_ttl_seconds <= 3600:
            raise ValueError("OIDC cache TTL must be between 1 and 3600 seconds")
        if not 1 <= self.max_cached_keys <= 64:
            raise ValueError("OIDC cache must contain between 1 and 64 keys")
        if not 0.1 <= self.http_timeout_seconds <= 30:
            raise ValueError("OIDC HTTP timeout must be between 0.1 and 30 seconds")


class JwksResolver(Protocol):
    async def resolve(self) -> Mapping[str, object]: ...


class HttpJwksResolver:
    """Bounded JWKS HTTP adapter; errors expose no response or token content."""

    def __init__(
        self,
        url: str,
        timeout_seconds: float,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._url = url
        self._client = client or httpx.AsyncClient(timeout=timeout_seconds)
        self._owns_client = client is None

    async def resolve(self) -> Mapping[str, object]:
        try:
            response = await self._client.get(self._url)
            response.raise_for_status()
            if len(response.content) > _MAX_JWKS_BYTES:
                raise AuthenticationError("jwks_response_too_large")
            payload = response.json()
        except AuthenticationError:
            raise
        except Exception as exc:
            raise AuthenticationError("jwks_unavailable") from exc
        keys = payload.get("keys") if isinstance(payload, dict) else None
        if not isinstance(keys, list):
            raise AuthenticationError("jwks_malformed")
        resolved: dict[str, object] = {}
        for key in keys:
            if not isinstance(key, dict):
                continue
            kid = key.get("kid")
            if isinstance(kid, str) and 0 < len(kid) <= 128:
                resolved[kid] = key
        return resolved

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


class OidcVerifier:
    def __init__(self, config: OidcConfig, resolver: JwksResolver) -> None:
        self._config = config
        self._resolver = resolver
        self._keys: dict[str, object] = {}
        self._expires_at = 0.0

    @property
    def cached_key_count(self) -> int:
        return len(self._keys)

    async def verify(self, token: str) -> Principal:
        if not token or len(token.encode("utf-8")) > _MAX_TOKEN_BYTES:
            raise AuthenticationError("token_too_large" if token else "malformed_token")
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise AuthenticationError("malformed_token") from exc
        algorithm = header.get("alg")
        if algorithm != self._config.algorithm or algorithm not in _ASYMMETRIC_ALGORITHMS:
            raise AuthenticationError("invalid_algorithm")
        kid = header.get("kid")
        if not isinstance(kid, str) or not kid or len(kid) > 128:
            raise AuthenticationError("missing_key_id")

        key = self._keys.get(kid) if monotonic() < self._expires_at else None
        if key is None:
            await self._refresh(kid)
            key = self._keys.get(kid)
        if key is None:
            raise AuthenticationError("unknown_key_id")
        if isinstance(key, dict):
            if key.get("alg") not in (None, self._config.algorithm):
                raise AuthenticationError("invalid_algorithm")
            if key.get("use") not in (None, "sig"):
                raise AuthenticationError("invalid_key_use")
        try:
            public_key = jwt.PyJWK.from_dict(key).key if isinstance(key, dict) else key
            claims = jwt.decode(
                token,
                public_key,
                algorithms=[self._config.algorithm],
                issuer=self._config.issuer,
                audience=self._config.audience,
                options={"require": ["iss", "aud", "sub", "exp"]},
            )
        except jwt.InvalidSignatureError as exc:
            raise AuthenticationError("invalid_signature") from exc
        except jwt.PyJWTError as exc:
            raise AuthenticationError("invalid_claims") from exc
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip() or len(subject) > 255:
            raise AuthenticationError("invalid_subject")
        return Principal(self._config.issuer, subject)

    async def _refresh(self, requested_kid: str) -> None:
        try:
            resolved = dict(await self._resolver.resolve())
        except AuthenticationError:
            raise
        except Exception as exc:
            raise AuthenticationError("jwks_unavailable") from exc
        selected: dict[str, object] = {}
        if requested_kid in resolved:
            selected[requested_kid] = resolved[requested_kid]
        for kid in sorted(resolved):
            if len(selected) >= self._config.max_cached_keys:
                break
            if kid != requested_kid and 0 < len(kid) <= 128:
                selected[kid] = resolved[kid]
        self._keys = selected
        self._expires_at = monotonic() + self._config.cache_ttl_seconds


def parse_bearer_token(value: str | None) -> str:
    if value is None:
        raise AuthenticationError("invalid_authorization_header")
    parts = value.split(" ")
    if len(parts) != 2 or parts[0].casefold() != "bearer" or not parts[1]:
        raise AuthenticationError("invalid_authorization_header")
    if len(parts[1].encode("utf-8")) > _MAX_TOKEN_BYTES:
        raise AuthenticationError("token_too_large")
    return parts[1]
