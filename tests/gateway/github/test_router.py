"""HTTP and audit integration tests for the GitHub webhook route."""

import hashlib
import hmac
import os
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aegisflow_core.control_plane.domain import AuditEvent, Tenant


BODY = b'{"action":"gate1b","installation":{"id":42},"repository":{"full_name":"owner/repo"},"client_payload":{}}'
SECRET = "test-webhook-secret"


def _headers(delivery_id: str, *, signature: str | None = None) -> dict[str, str]:
    resolved_signature = signature or (
        "sha256="
        + hmac.new(SECRET.encode(), BODY, hashlib.sha256).hexdigest()
    )
    return {
        "X-Hub-Signature-256": resolved_signature,
        "X-GitHub-Event": "repository_dispatch",
        "X-GitHub-Delivery": delivery_id,
        "Content-Type": "application/json",
    }


@pytest.mark.anyio
async def test_route_is_unavailable_without_github_configuration(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post("/webhooks/github", content=BODY)

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "reason": "github_app_not_configured",
    }


@pytest.mark.database
@pytest.mark.anyio
async def test_route_audits_allow_deny_and_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    monkeypatch.setenv("APP_ENV", "test")
    slug = f"af201-router-{uuid4()}"
    delivery = f"delivery-{uuid4()}"
    monkeypatch.setenv("GITHUB_APP_ID", "123")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "test-private-key")
    monkeypatch.setenv("GITHUB_APP_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "42")
    monkeypatch.setenv("AEGISFLOW_BOOTSTRAP_TENANT_SLUG", slug)

    from aegisflow_core.app import create_app

    app = create_app()
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        sessions = async_sessionmaker(
            connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        app.state.session_factory = sessions
        try:
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as test_client:
                invalid = await test_client.post(
                    "/webhooks/github",
                    content=BODY,
                    headers=_headers(delivery, signature="sha256=invalid"),
                )
                accepted = await test_client.post(
                    "/webhooks/github", content=BODY, headers=_headers(delivery)
                )
                duplicate = await test_client.post(
                    "/webhooks/github", content=BODY, headers=_headers(delivery)
                )

            assert invalid.status_code == 401
            assert accepted.status_code == 202
            assert accepted.json() == {"status": "accepted"}
            assert duplicate.status_code == 409
            assert duplicate.json()["reason"] == "duplicate_delivery"

            async with sessions() as session:
                tenant_id = await session.scalar(
                    select(Tenant.id).where(Tenant.slug == slug)
                )
                events = list(
                    await session.scalars(
                        select(AuditEvent)
                        .where(AuditEvent.tenant_id == tenant_id)
                        .order_by(AuditEvent.created_at)
                    )
                )
            assert [(event.decision, event.reason) for event in events] == [
                ("deny", "invalid_signature"),
                ("allow", "allow"),
                ("deny", "duplicate_delivery"),
            ]
        finally:
            await transaction.rollback()
    await app.state.database_engine.dispose()
    await engine.dispose()
