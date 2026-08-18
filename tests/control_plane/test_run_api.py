"""HTTP contract for the local MVP Run lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
import pytest

from aegisflow_core.app import create_app
from aegisflow_core.control_plane.runs import (
    CreateRunRequest,
    RepositoryInput,
    RunDetail,
    RunEventView,
    RunList,
    RunServiceUnavailable,
    RunSummary,
    SessionView,
)
from aegisflow_core.control_plane.run_service import IdempotencyConflictError

TENANT_ID = UUID("10000000-0000-0000-0000-000000000001")
RUN_ID = UUID("20000000-0000-0000-0000-000000000002")
NOW = datetime(2026, 8, 17, tzinfo=timezone.utc)
DEV_TOKEN = "local-developer-token-123"
REVIEW_TOKEN = "local-reviewer-token-456"


def headers(persona: str = "developer") -> dict[str, str]:
    return {
        "X-AegisFlow-Local-Persona": persona,
        "X-AegisFlow-Local-Token": DEV_TOKEN if persona == "developer" else REVIEW_TOKEN,
    }


def payload() -> dict[str, Any]:
    return CreateRunRequest(
        source_type="prd",
        source_ref="local://prd/first",
        title="Add a governed delivery status endpoint",
        body=(
            "Create a tenant-scoped status endpoint with tests, audit evidence, "
            "and a separate Reviewer approval before any write occurs."
        ),
        repository=RepositoryInput(
            owner="KinguYume-G", name="AegisFlow", base_ref="main", base_sha="a" * 40
        ),
    ).model_dump(mode="json")


def summary(status: str = "running") -> RunSummary:
    return RunSummary(
        run_id=RUN_ID,
        tenant_id=TENANT_ID,
        status=status,
        source_type="prd",
        title="Add a governed delivery status endpoint",
        requested_by="urn:aegisflow:local-mvp|developer",
        created_at=NOW,
        updated_at=NOW,
    )


class FakeRunService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.failure: Exception | None = None

    def fail_next(self, error: Exception) -> None:
        self.failure = error

    def _raise_failure(self) -> None:
        if self.failure is None:
            return
        error = self.failure
        self.failure = None
        raise error

    async def session(self, principal: object) -> SessionView:
        self._raise_failure()
        subject = getattr(principal, "subject")
        return SessionView(
            actor_reference=f"urn:aegisflow:local-mvp|{subject}",
            profile="local_mvp",
            tenants=[
                {
                    "tenant_id": TENANT_ID,
                    "slug": "local-mvp",
                    "roles": ["Developer" if subject == "developer" else "Reviewer"],
                    "capabilities": ["run:read"],
                }
            ],
        )

    async def create_run(self, tenant_id, principal, request, idempotency_key):
        self._raise_failure()
        self.calls.append(("create", (tenant_id, principal.subject, idempotency_key)))
        if principal.subject != "developer":
            raise PermissionError("tenant_access_denied")
        return RunDetail(summary=summary(), request=request)

    async def list_runs(self, tenant_id, principal, limit):
        self._raise_failure()
        self.calls.append(("list", (tenant_id, principal.subject, limit)))
        return RunList(items=[summary()], next_cursor=None)

    async def get_run(self, tenant_id, principal, run_id):
        self._raise_failure()
        self.calls.append(("get", (tenant_id, principal.subject, run_id)))
        return RunDetail(summary=summary(), request=CreateRunRequest.model_validate(payload()))

    async def list_events(self, tenant_id, principal, run_id, after, limit):
        self._raise_failure()
        self.calls.append(("events", (run_id, after, limit)))
        return [
            RunEventView(
                sequence=2,
                event_type="run.started",
                actor="system",
                payload={"status": "running"},
                created_at=NOW,
            )
        ]

    async def submit_clarification(
        self, tenant_id, principal, run_id, request_id, answers, signal_id
    ):
        self._raise_failure()
        self.calls.append(("clarification", (principal.subject, request_id, answers, signal_id)))
        return {"accepted": True, "run_id": str(run_id), "status": "waiting_clarification"}

    async def submit_approval(
        self, tenant_id, principal, run_id, approval_id, decision, reason, signal_id
    ):
        self._raise_failure()
        self.calls.append(("approval", (principal.subject, approval_id, decision, reason, signal_id)))
        if principal.subject != "reviewer":
            raise PermissionError("rbac_self_approval_forbidden")
        return {"accepted": True, "run_id": str(run_id), "status": "waiting_approval"}


@pytest.fixture
def local_env(valid_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCAL_MVP_PROFILE_ENABLED", "true")
    monkeypatch.setenv("LOCAL_MVP_DEVELOPER_TOKEN", DEV_TOKEN)
    monkeypatch.setenv("LOCAL_MVP_REVIEWER_TOKEN", REVIEW_TOKEN)
    monkeypatch.setenv("LOCAL_MVP_GITHUB_DRY_RUN", "true")


@pytest.fixture
async def local_client(local_env: None):
    app = create_app()
    service = FakeRunService()
    app.state.run_service = service
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, service


@pytest.mark.anyio
async def test_profile_and_session_expose_mode_without_tokens(local_client) -> None:
    client, _ = local_client
    profile = await client.get("/v1/system/profile")
    session = await client.get("/v1/session", headers=headers())

    assert profile.status_code == 200
    assert profile.json() == {
        "profile": "local_mvp",
        "github_effect_mode": "dry_run",
        "model_mode": "disabled",
    }
    assert DEV_TOKEN not in profile.text
    assert REVIEW_TOKEN not in profile.text
    assert session.status_code == 200
    assert session.json()["tenants"][0]["tenant_id"] == str(TENANT_ID)


@pytest.mark.anyio
async def test_create_list_detail_graph_and_event_polling(local_client) -> None:
    client, service = local_client
    created = await client.post(
        f"/v1/tenants/{TENANT_ID}/runs",
        headers={**headers(), "Idempotency-Key": "create-run-00000001"},
        json=payload(),
    )
    listed = await client.get(f"/v1/tenants/{TENANT_ID}/runs?limit=20", headers=headers())
    detail = await client.get(f"/v1/tenants/{TENANT_ID}/runs/{RUN_ID}", headers=headers())
    events = await client.get(
        f"/v1/tenants/{TENANT_ID}/runs/{RUN_ID}/events?after=1&limit=20",
        headers=headers(),
    )

    assert created.status_code == 202 and created.json()["summary"]["run_id"] == str(RUN_ID)
    assert listed.status_code == 200 and len(listed.json()["items"]) == 1
    assert detail.status_code == 200 and detail.json()["request"]["source_type"] == "prd"
    assert events.status_code == 200 and events.json()[0]["sequence"] == 2
    assert any(call[0] == "create" for call in service.calls)


@pytest.mark.anyio
async def test_local_identity_is_required_and_persona_is_bound(local_client) -> None:
    client, _ = local_client
    missing = await client.get(f"/v1/tenants/{TENANT_ID}/runs")
    swapped = await client.get(
        f"/v1/tenants/{TENANT_ID}/runs",
        headers={
            "X-AegisFlow-Local-Persona": "developer",
            "X-AegisFlow-Local-Token": REVIEW_TOKEN,
        },
    )

    assert missing.status_code == 401
    assert swapped.status_code == 401
    assert "token" not in missing.text.casefold()


@pytest.mark.anyio
async def test_clarification_and_separate_reviewer_approval(local_client) -> None:
    client, _ = local_client
    clarification_id = UUID("30000000-0000-0000-0000-000000000003")
    approval_id = UUID("40000000-0000-0000-0000-000000000004")
    clarified = await client.post(
        f"/v1/tenants/{TENANT_ID}/runs/{RUN_ID}/clarifications/{clarification_id}",
        headers={**headers(), "Idempotency-Key": "clarify-000000001"},
        json={"answers": {"acceptance_criteria": "Tests and audit must pass."}},
    )
    self_approval = await client.post(
        f"/v1/tenants/{TENANT_ID}/runs/{RUN_ID}/approvals/{approval_id}",
        headers={**headers(), "Idempotency-Key": "approval-00000001"},
        json={"decision": "approved", "reason": "looks safe"},
    )
    reviewed = await client.post(
        f"/v1/tenants/{TENANT_ID}/runs/{RUN_ID}/approvals/{approval_id}",
        headers={**headers("reviewer"), "Idempotency-Key": "approval-00000002"},
        json={"decision": "approved", "reason": "scope and tests verified"},
    )

    assert clarified.status_code == 202
    assert self_approval.status_code == 403
    assert reviewed.status_code == 202


@pytest.mark.anyio
async def test_api_rejects_missing_idempotency_and_unknown_fields(local_client) -> None:
    client, _ = local_client
    missing_key = await client.post(
        f"/v1/tenants/{TENANT_ID}/runs", headers=headers(), json=payload()
    )
    invalid = payload()
    invalid["tenant_id"] = str(UUID(int=1))
    unknown = await client.post(
        f"/v1/tenants/{TENANT_ID}/runs",
        headers={**headers(), "Idempotency-Key": "create-run-00000002"},
        json=invalid,
    )

    assert missing_key.status_code == 422
    assert unknown.status_code == 422


@pytest.mark.anyio
async def test_run_routes_map_expected_domain_failures_without_leaking_details(
    local_client,
) -> None:
    client, service = local_client
    clarification_id = UUID("30000000-0000-0000-0000-000000000003")
    approval_id = UUID("40000000-0000-0000-0000-000000000004")

    async def call_with_failure(error: Exception, method: str, path: str, **kwargs):
        service.fail_next(error)
        return await client.request(method, path, **kwargs)

    cases = [
        await call_with_failure(
            RunServiceUnavailable(), "GET", "/v1/session", headers=headers()
        ),
        await call_with_failure(
            IdempotencyConflictError(),
            "POST",
            f"/v1/tenants/{TENANT_ID}/runs",
            headers={**headers(), "Idempotency-Key": "create-conflict-001"},
            json=payload(),
        ),
        await call_with_failure(
            RunServiceUnavailable(),
            "POST",
            f"/v1/tenants/{TENANT_ID}/runs",
            headers={**headers(), "Idempotency-Key": "create-unavailable-001"},
            json=payload(),
        ),
        await call_with_failure(
            PermissionError("tenant_access_denied"),
            "GET",
            f"/v1/tenants/{TENANT_ID}/runs",
            headers=headers(),
        ),
        await call_with_failure(
            RunServiceUnavailable(),
            "GET",
            f"/v1/tenants/{TENANT_ID}/runs",
            headers=headers(),
        ),
        await call_with_failure(
            KeyError(RUN_ID),
            "GET",
            f"/v1/tenants/{TENANT_ID}/runs/{RUN_ID}",
            headers=headers(),
        ),
        await call_with_failure(
            PermissionError("tenant_access_denied"),
            "GET",
            f"/v1/tenants/{TENANT_ID}/runs/{RUN_ID}",
            headers=headers(),
        ),
        await call_with_failure(
            RunServiceUnavailable(),
            "GET",
            f"/v1/tenants/{TENANT_ID}/runs/{RUN_ID}",
            headers=headers(),
        ),
        await call_with_failure(
            KeyError(RUN_ID),
            "GET",
            f"/v1/tenants/{TENANT_ID}/runs/{RUN_ID}/events",
            headers=headers(),
        ),
        await call_with_failure(
            PermissionError("tenant_access_denied"),
            "GET",
            f"/v1/tenants/{TENANT_ID}/runs/{RUN_ID}/events",
            headers=headers(),
        ),
        await call_with_failure(
            PermissionError("tenant_access_denied"),
            "POST",
            f"/v1/tenants/{TENANT_ID}/runs/{RUN_ID}/clarifications/{clarification_id}",
            headers={**headers(), "Idempotency-Key": "clarification-denied-001"},
            json={"answers": {"scope": "bounded"}},
        ),
        await call_with_failure(
            ValueError("invalid clarification"),
            "POST",
            f"/v1/tenants/{TENANT_ID}/runs/{RUN_ID}/clarifications/{clarification_id}",
            headers={**headers(), "Idempotency-Key": "clarification-conflict-001"},
            json={"answers": {"scope": "bounded"}},
        ),
        await call_with_failure(
            ValueError("invalid approval"),
            "POST",
            f"/v1/tenants/{TENANT_ID}/runs/{RUN_ID}/approvals/{approval_id}",
            headers={**headers("reviewer"), "Idempotency-Key": "approval-conflict-001"},
            json={"decision": "approved", "reason": "reviewed"},
        ),
    ]

    assert [response.status_code for response in cases] == [
        503,
        409,
        503,
        403,
        503,
        404,
        403,
        503,
        404,
        403,
        403,
        409,
        409,
    ]
    assert all("invalid clarification" not in response.text for response in cases)
    assert all("invalid approval" not in response.text for response in cases)


@pytest.mark.anyio
async def test_session_reports_identity_configuration_failure(client) -> None:
    response = await client.get("/v1/session")

    assert response.status_code == 503
    assert response.json() == {"error": {"code": "identity_not_configured"}}
