"""AF-409 cross-tenant isolation contract across in-process adapters."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from aegisflow_core.control_plane.domain.knowledge import RepositoryChunk
from aegisflow_core.control_plane.identity import Principal
from aegisflow_core.control_plane.rbac import AuthorizationDecision, Capability
from aegisflow_core.gateway.tenant import resolve_tenant_scope
from aegisflow_core.packs.delivery.contracts.normalized_request import NormalizedRequest
from aegisflow_core.runtime.context.pgvector_retriever import (
    ContextIsolationViolation,
    PgVectorContextRetriever,
    RepositoryTarget,
)
from aegisflow_core.runtime.tracing import (
    InMemoryTraceRecorder,
    build_step_trace_record,
    unavailable_cost_usage,
    unavailable_token_usage,
)


class TenantLocalAuthorizer:
    def __init__(self, memberships: set[tuple[object, str]]) -> None:
        self._memberships = memberships

    async def authorize(self, tenant_id, principal, capability):  # type: ignore[no-untyped-def]
        allowed = (tenant_id, principal.actor_reference) in self._memberships
        return AuthorizationDecision(
            allowed, "rbac_allowed" if allowed else "rbac_membership_missing", capability
        )


def request() -> NormalizedRequest:
    return NormalizedRequest(
        source_type="github_issue",
        source_ref="same/resource",
        title="same name",
        body="same body",
        idempotency_key="a" * 64,
        received_at=datetime.now(timezone.utc),
    )


def chunk(tenant_id, repository: str) -> RepositoryChunk:  # type: ignore[no-untyped-def]
    return RepositoryChunk(
        tenant_id=tenant_id,
        repository=repository,
        file_path="same/path.py",
        chunk_index=0,
        content_hash="b" * 64,
        content="tenant-private-content",
        start_line=1,
        end_line=1,
        embedding=[0.0] * 32,
    )


@pytest.mark.anyio
async def test_api_scope_requires_verified_tenant_local_membership() -> None:
    tenant_a, tenant_b = uuid4(), uuid4()
    principal = Principal("https://issuer.example.test", "same-subject")
    authorizer = TenantLocalAuthorizer({(tenant_a, principal.actor_reference)})

    scope = await resolve_tenant_scope(
        tenant_id=tenant_a,
        principal=principal,
        capability=Capability.RUN_READ,
        authorizer=authorizer,
    )
    assert scope.tenant_id == tenant_a
    for candidate in (None, tenant_b):
        with pytest.raises(PermissionError, match="^tenant_access_denied$"):
            await resolve_tenant_scope(
                tenant_id=candidate,
                principal=principal,
                capability=Capability.RUN_READ,
                authorizer=authorizer,
            )


def test_rag_rejects_adapter_rows_from_another_namespace() -> None:
    tenant_a, tenant_b = uuid4(), uuid4()
    retriever = PgVectorContextRetriever(
        tenant_id=tenant_a,
        target=RepositoryTarget("same", "repo"),
        query=lambda *_: [chunk(tenant_b, "same/repo")],
    )
    with pytest.raises(ContextIsolationViolation, match="namespace mismatch"):
        retriever.retrieve(request())

    wrong_repository = PgVectorContextRetriever(
        tenant_id=tenant_a,
        target=RepositoryTarget("same", "repo"),
        query=lambda *_: [chunk(tenant_a, "other/repo")],
    )
    with pytest.raises(ContextIsolationViolation, match="namespace mismatch"):
        wrong_repository.retrieve(request())


def _trace(tenant_id):  # type: ignore[no-untyped-def]
    return build_step_trace_record(
        tenant_id=tenant_id,
        workflow_id=uuid4(),
        workflow_version=1,
        run_id=uuid4(),
        step_id=uuid4(),
        trace_id=uuid4(),
        agent="context",
        raw_prompt="same prompt",
        model="deterministic-fake",
        token_usage=unavailable_token_usage(),
        cost=unavailable_cost_usage(),
        latency_ms=1,
    )


def test_trace_query_is_tenant_scoped_with_colliding_shapes() -> None:
    tenant_a, tenant_b = uuid4(), uuid4()
    recorder = InMemoryTraceRecorder()
    record_a, record_b = _trace(tenant_a), _trace(tenant_b)
    recorder.record(record_a)
    recorder.record(record_b)

    assert recorder.records_for_tenant(tenant_a) == (record_a,)
    assert recorder.records_for_tenant(tenant_b) == (record_b,)
    with pytest.raises(ValueError, match="tenant_id is required"):
        recorder.records_for_tenant(None)  # type: ignore[arg-type]


@pytest.mark.anyio
async def test_parallel_scope_resolution_has_no_ambient_tenant_leakage() -> None:
    tenant_a, tenant_b = uuid4(), uuid4()
    principal_a = Principal("https://issuer.example.test", "a")
    principal_b = Principal("https://issuer.example.test", "b")
    authorizer = TenantLocalAuthorizer(
        {
            (tenant_a, principal_a.actor_reference),
            (tenant_b, principal_b.actor_reference),
        }
    )

    async def resolve(tenant_id, principal):  # type: ignore[no-untyped-def]
        await asyncio.sleep(0)
        return await resolve_tenant_scope(
            tenant_id=tenant_id,
            principal=principal,
            capability=Capability.RUN_READ,
            authorizer=authorizer,
        )

    scopes = await asyncio.gather(
        *(resolve(tenant_a, principal_a) for _ in range(20)),
        *(resolve(tenant_b, principal_b) for _ in range(20)),
    )
    assert [scope.tenant_id for scope in scopes[:20]] == [tenant_a] * 20
    assert [scope.tenant_id for scope in scopes[20:]] == [tenant_b] * 20
