"""HTTP contracts for OIDC-to-opaque Console session exchange and revocation."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy.exc import SQLAlchemyError

from aegisflow_core.app import create_app
from aegisflow_core.control_plane.identity import (
    AuthenticationError,
    Principal,
    VerifiedIdentity,
)
from aegisflow_core.control_plane.identity.sessions import (
    CreatedConsoleSession,
    SessionAuthenticationError,
    SessionAuthorizationError,
)


NOW = datetime(2026, 8, 18, 6, 0, tzinfo=timezone.utc)
RAW_SESSION = "afs_cs_" + "D" * 43
PRINCIPAL = Principal("https://issuer.example.test", "developer-1")


class FakeOidcVerifier:
    async def verify_identity(self, token: str) -> VerifiedIdentity:
        if token != "provider-access-token":
            raise AuthenticationError("invalid_claims")
        return VerifiedIdentity(PRINCIPAL, NOW + timedelta(minutes=5))


class FakeSessionManager:
    def __init__(self) -> None:
        self.revoked: list[str] = []
        self.create_failure: Exception | None = None
        self.authentication_failure: Exception | None = None

    async def create(self, identity: VerifiedIdentity) -> CreatedConsoleSession:
        if self.create_failure is not None:
            raise self.create_failure
        assert identity.principal == PRINCIPAL
        return CreatedConsoleSession(RAW_SESSION, identity.expires_at, PRINCIPAL)

    async def authenticate(self, token: str) -> Principal:
        if self.authentication_failure is not None:
            raise self.authentication_failure
        if token != RAW_SESSION:
            raise SessionAuthenticationError("invalid_session")
        return PRINCIPAL

    async def revoke(self, token: str) -> bool:
        if token != RAW_SESSION:
            raise SessionAuthenticationError("invalid_session")
        self.revoked.append(token)
        return len(self.revoked) == 1


class FakeSessionFactory:
    @asynccontextmanager
    async def begin(self):
        yield object()


class BrokenSessionFactory:
    @asynccontextmanager
    async def begin(self):
        raise SQLAlchemyError("database connection detail")
        yield object()


class FakeRunService:
    async def session(self, principal: Principal):
        assert principal == PRINCIPAL
        return {
            "actor_reference": principal.actor_reference,
            "profile": "oidc",
            "tenants": [],
        }


@pytest.fixture
async def auth_client(valid_env: None):
    app = create_app()
    manager = FakeSessionManager()
    app.state.oidc_verifier = FakeOidcVerifier()
    app.state.session_factory = FakeSessionFactory()
    app.state.console_session_manager_factory = lambda _session: manager
    app.state.run_service = FakeRunService()
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, manager


@pytest.mark.anyio
async def test_exchange_verified_bearer_for_no_store_opaque_session(auth_client) -> None:
    client, _ = auth_client

    response = await client.post(
        "/v1/auth/sessions",
        headers={"Authorization": "Bearer provider-access-token"},
    )

    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "session_token": RAW_SESSION,
        "expires_at": (NOW + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
        "actor_reference": PRINCIPAL.actor_reference,
    }
    assert "provider-access-token" not in response.text


@pytest.mark.anyio
async def test_opaque_session_authenticates_existing_routes_and_logout_is_idempotent(
    auth_client,
) -> None:
    client, manager = auth_client
    headers = {"Authorization": f"AegisSession {RAW_SESSION}"}

    session = await client.get("/v1/session", headers=headers)
    first = await client.delete("/v1/auth/session", headers=headers)
    repeated = await client.delete("/v1/auth/session", headers=headers)

    assert session.status_code == 200
    assert session.json()["actor_reference"] == PRINCIPAL.actor_reference
    assert first.status_code == repeated.status_code == 204
    assert manager.revoked == [RAW_SESSION, RAW_SESSION]


@pytest.mark.anyio
async def test_session_endpoints_fail_closed_with_stable_errors(auth_client) -> None:
    client, manager = auth_client
    missing = await client.post("/v1/auth/sessions")
    invalid_bearer = await client.post(
        "/v1/auth/sessions", headers={"Authorization": "Bearer wrong-token"}
    )
    wrong_scheme = await client.post(
        "/v1/auth/sessions", headers={"Authorization": f"AegisSession {RAW_SESSION}"}
    )

    manager.create_failure = SessionAuthorizationError("session_membership_required")
    no_membership = await client.post(
        "/v1/auth/sessions",
        headers={"Authorization": "Bearer provider-access-token"},
    )
    manager.create_failure = None
    manager.authentication_failure = SessionAuthenticationError("session_expired")
    expired = await client.get(
        "/v1/session", headers={"Authorization": f"AegisSession {RAW_SESSION}"}
    )
    ambiguous = await client.get(
        "/v1/session",
        headers={
            "Authorization": f"AegisSession {RAW_SESSION}",
            "X-AegisFlow-Local-Persona": "developer",
            "X-AegisFlow-Local-Token": "local-developer-token-123",
        },
    )

    assert missing.status_code == 401
    assert invalid_bearer.status_code == 401
    assert wrong_scheme.status_code == 401
    assert no_membership.status_code == 403
    assert expired.status_code == 401
    assert ambiguous.status_code == 401
    assert [
        response.json()["error"]["code"]
        for response in (
            missing,
            invalid_bearer,
            wrong_scheme,
            no_membership,
            expired,
            ambiguous,
        )
    ] == [
        "invalid_authorization_header",
        "invalid_claims",
        "invalid_authorization_header",
        "session_membership_required",
        "session_expired",
        "ambiguous_identity",
    ]
    combined = "".join(response.text for response in (missing, invalid_bearer, expired))
    assert "provider-access-token" not in combined
    assert RAW_SESSION not in combined


@pytest.mark.anyio
async def test_session_exchange_sanitizes_database_unavailability(auth_client) -> None:
    client, _ = auth_client
    app = client._transport.app
    app.state.session_factory = BrokenSessionFactory()

    response = await client.post(
        "/v1/auth/sessions",
        headers={"Authorization": "Bearer provider-access-token"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "session_store_unavailable"
    assert "database connection detail" not in response.text
