"""PostgreSQL Run service keeps lifecycle facts tenant-scoped and idempotent."""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aegisflow_core.control_plane.bootstrap import bootstrap_local_mvp
from aegisflow_core.control_plane.domain import (
    Approval,
    ClarificationRequest,
    RoleAssignment,
)
from aegisflow_core.control_plane.identity import Principal
from aegisflow_core.control_plane.run_service import (
    IdempotencyConflictError,
    PostgresRunService,
)
from aegisflow_core.control_plane.run_projection import PostgresRunProjection
from aegisflow_core.control_plane.runs import CreateRunRequest, RepositoryInput


class TemporalGateway:
    def __init__(self) -> None:
        self.started = []
        self.clarifications = []
        self.approvals = []

    async def start(self, workflow_input) -> None:
        self.started.append(workflow_input)

    async def signal_clarification(self, identity, signal) -> None:
        self.clarifications.append((identity, signal))

    async def signal_approval(self, identity, signal) -> None:
        self.approvals.append((identity, signal))


def principal(subject: str) -> Principal:
    return Principal("urn:aegisflow:local-mvp", subject)


def input_request(title: str = "Implement a governed status endpoint") -> CreateRunRequest:
    return CreateRunRequest(
        source_type="prd",
        source_ref="local://prd/run-service",
        title=title,
        body=(
            "Implement one tenant-scoped endpoint with bounded output, automated tests, "
            "audit evidence, and a separate Reviewer approval before any write."
        ),
        repository=RepositoryInput(
            owner="KinguYume-G", name="AegisFlow", base_ref="main", base_sha="a" * 40
        ),
    )


@pytest.mark.database
@pytest.mark.anyio
async def test_run_create_replay_list_detail_session_and_cross_tenant_denial() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        sessions = async_sessionmaker(
            connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        temporal = TemporalGateway()
        try:
            async with sessions.begin() as session:
                bootstrap = await bootstrap_local_mvp(
                    session,
                    slug=f"local-run-service-{uuid4()}",
                    developer=principal("developer"),
                    reviewer=principal("reviewer"),
                )
                other = await bootstrap_local_mvp(
                    session,
                    slug=f"local-run-service-other-{uuid4()}",
                    developer=Principal("urn:aegisflow:other", "developer"),
                    reviewer=Principal("urn:aegisflow:other", "reviewer"),
                )
            service = PostgresRunService(sessions, temporal, profile="local_mvp")

            created = await service.create_run(
                bootstrap.tenant_id,
                principal("developer"),
                input_request(),
                "run-service-idempotency-001",
            )
            replayed = await service.create_run(
                bootstrap.tenant_id,
                principal("developer"),
                input_request(),
                "run-service-idempotency-001",
            )
            listed = await service.list_runs(
                bootstrap.tenant_id, principal("developer"), 20
            )
            detail = await service.get_run(
                bootstrap.tenant_id, principal("reviewer"), created.summary.run_id
            )
            events = await service.list_events(
                bootstrap.tenant_id,
                principal("developer"),
                created.summary.run_id,
                0,
                20,
            )
            session = await service.session(principal("developer"))

            assert created.summary.run_id == replayed.summary.run_id
            assert created.summary.status == "running"
            assert len(temporal.started) == 1
            assert temporal.started[0].identity.run_id == str(created.summary.run_id)
            assert [item.run_id for item in listed.items] == [created.summary.run_id]
            assert detail.request.repository.name == "AegisFlow"
            assert [event.event_type for event in events] == ["run.created", "run.started"]
            assert session.profile == "local_mvp"
            assert session.tenants[0].tenant_id == bootstrap.tenant_id
            assert "Developer" in session.tenants[0].roles

            with pytest.raises(IdempotencyConflictError):
                await service.create_run(
                    bootstrap.tenant_id,
                    principal("developer"),
                    input_request("Changed title cannot reuse the key"),
                    "run-service-idempotency-001",
                )
            with pytest.raises(PermissionError, match="tenant_access_denied"):
                await service.list_runs(
                    other.tenant_id, principal("developer"), 20
                )
            with pytest.raises(PermissionError, match="tenant_access_denied"):
                await service.create_run(
                    bootstrap.tenant_id,
                    principal("reviewer"),
                    input_request(),
                    "reviewer-cannot-create-001",
                )
        finally:
            await transaction.rollback()
    await engine.dispose()


@pytest.mark.database
@pytest.mark.anyio
async def test_run_idempotency_is_tenant_local() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        sessions = async_sessionmaker(
            connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        temporal = TemporalGateway()
        try:
            bootstraps = []
            async with sessions.begin() as session:
                for index in range(2):
                    issuer = f"urn:aegisflow:tenant-{index}"
                    bootstraps.append(
                        await bootstrap_local_mvp(
                            session,
                            slug=f"local-idempotency-{uuid4()}",
                            developer=Principal(issuer, "developer"),
                            reviewer=Principal(issuer, "reviewer"),
                        )
                    )
            service = PostgresRunService(sessions, temporal, profile="local_mvp")
            ids: list[UUID] = []
            for index, bootstrap in enumerate(bootstraps):
                value = await service.create_run(
                    bootstrap.tenant_id,
                    Principal(f"urn:aegisflow:tenant-{index}", "developer"),
                    input_request(),
                    "same-key-across-tenants",
                )
                ids.append(value.summary.run_id)
            assert ids[0] != ids[1]
            assert len(temporal.started) == 2
        finally:
            await transaction.rollback()
    await engine.dispose()


@pytest.mark.database
@pytest.mark.anyio
async def test_clarification_signal_is_validated_tenant_scoped_and_idempotent() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        sessions = async_sessionmaker(
            connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        temporal = TemporalGateway()
        try:
            async with sessions.begin() as session:
                bootstrap = await bootstrap_local_mvp(
                    session,
                    slug=f"local-clarification-{uuid4()}",
                    developer=principal("developer"),
                    reviewer=principal("reviewer"),
                )
            service = PostgresRunService(sessions, temporal, profile="local_mvp")
            created = await service.create_run(
                bootstrap.tenant_id,
                principal("developer"),
                input_request(),
                "clarification-run-001",
            )
            request_id = uuid4()
            async with sessions.begin() as session:
                session.add(
                    ClarificationRequest(
                        id=request_id,
                        tenant_id=bootstrap.tenant_id,
                        run_id=created.summary.run_id,
                        step_key="clarifier",
                        questions=[
                            {
                                "id": "acceptance_criteria",
                                "question": "Which evidence proves completion?",
                            }
                        ],
                        status="pending",
                    )
                )

            detail = await service.get_run(
                bootstrap.tenant_id, principal("developer"), created.summary.run_id
            )
            assert detail.pending_action == {
                "kind": "clarification",
                "request_id": str(request_id),
                "questions": [
                    {
                        "id": "acceptance_criteria",
                        "question": "Which evidence proves completion?",
                    }
                ],
            }

            with pytest.raises(ValueError, match="clarification answers are invalid"):
                await service.submit_clarification(
                    bootstrap.tenant_id,
                    principal("developer"),
                    created.summary.run_id,
                    request_id,
                    {},
                    "clarification-empty-001",
                )
            with pytest.raises(ValueError, match="clarification answers are invalid"):
                await service.submit_clarification(
                    bootstrap.tenant_id,
                    principal("developer"),
                    created.summary.run_id,
                    request_id,
                    {"acceptance_criteria": " "},
                    "clarification-blank-001",
                )
            with pytest.raises(KeyError):
                await service.submit_clarification(
                    bootstrap.tenant_id,
                    principal("developer"),
                    created.summary.run_id,
                    uuid4(),
                    {"acceptance_criteria": "Tests and audit evidence."},
                    "clarification-missing-001",
                )

            result = await service.submit_clarification(
                bootstrap.tenant_id,
                principal("developer"),
                created.summary.run_id,
                request_id,
                {"acceptance_criteria": "Tests and audit evidence."},
                "clarification-signal-001",
            )
            replay = await service.submit_clarification(
                bootstrap.tenant_id,
                principal("developer"),
                created.summary.run_id,
                request_id,
                {"acceptance_criteria": "Tests and audit evidence."},
                "clarification-signal-001",
            )

            assert result["status"] == "waiting_clarification"
            assert replay["status"] == "running"
            assert len(temporal.clarifications) == 1
            _, signal = temporal.clarifications[0]
            assert signal.target_reference == str(request_id)
            assert "Tests and audit evidence." in signal.value
            events = await service.list_events(
                bootstrap.tenant_id,
                principal("developer"),
                created.summary.run_id,
                0,
                20,
            )
            assert [event.event_type for event in events].count(
                "human.clarification.submitted"
            ) == 1

            with pytest.raises(KeyError):
                await service.get_run(
                    bootstrap.tenant_id, principal("developer"), uuid4()
                )
            with pytest.raises(KeyError):
                await service.list_events(
                    bootstrap.tenant_id, principal("developer"), uuid4(), 0, 20
                )
        finally:
            await transaction.rollback()
    await engine.dispose()


@pytest.mark.database
@pytest.mark.anyio
async def test_approval_requires_a_separate_reviewer_and_is_idempotent() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        sessions = async_sessionmaker(
            connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        temporal = TemporalGateway()
        try:
            async with sessions.begin() as session:
                bootstrap = await bootstrap_local_mvp(
                    session,
                    slug=f"local-approval-{uuid4()}",
                    developer=principal("developer"),
                    reviewer=principal("reviewer"),
                )
                # Defense in depth: even a requester who also holds Reviewer
                # must not approve their own external side effect.
                session.add(
                    RoleAssignment(
                        tenant_id=bootstrap.tenant_id,
                        membership_id=bootstrap.developer_membership_id,
                        role="Reviewer",
                        assigned_by="test:dual-role",
                    )
                )
            service = PostgresRunService(sessions, temporal, profile="local_mvp")
            created = await service.create_run(
                bootstrap.tenant_id,
                principal("developer"),
                input_request(),
                "approval-run-001",
            )
            approval_id = uuid4()
            async with sessions.begin() as session:
                session.add(
                    Approval(
                        id=approval_id,
                        tenant_id=bootstrap.tenant_id,
                        run_id=created.summary.run_id,
                        step_id=None,
                        decision="pending",
                        reason="Draft PR requires an independent reviewer.",
                        action_preview={
                            "tool": "github.create_draft_pr",
                            "repository": "KinguYume-G/AegisFlow",
                        },
                        action_digest="b" * 64,
                    )
                )

            detail = await service.get_run(
                bootstrap.tenant_id, principal("reviewer"), created.summary.run_id
            )
            assert detail.pending_action is not None
            assert detail.pending_action["kind"] == "approval"
            assert detail.pending_action["request_id"] == str(approval_id)
            assert detail.pending_action["action_digest"] == "b" * 64

            with pytest.raises(PermissionError, match="rbac_self_approval_forbidden"):
                await service.submit_approval(
                    bootstrap.tenant_id,
                    principal("developer"),
                    created.summary.run_id,
                    approval_id,
                    "approved",
                    "Self approval must be denied.",
                    "approval-self-001",
                )
            with pytest.raises(KeyError):
                await service.submit_approval(
                    bootstrap.tenant_id,
                    principal("reviewer"),
                    created.summary.run_id,
                    uuid4(),
                    "approved",
                    "Unknown approval.",
                    "approval-missing-001",
                )

            result = await service.submit_approval(
                bootstrap.tenant_id,
                principal("reviewer"),
                created.summary.run_id,
                approval_id,
                "approved",
                "Scope, tests and side effects verified.",
                "approval-signal-001",
            )
            replay = await service.submit_approval(
                bootstrap.tenant_id,
                principal("reviewer"),
                created.summary.run_id,
                approval_id,
                "approved",
                "Scope, tests and side effects verified.",
                "approval-signal-001",
            )

            assert result["status"] == "waiting_approval"
            assert replay["status"] == "running"
            assert len(temporal.approvals) == 1
            _, signal = temporal.approvals[0]
            assert signal.target_reference == str(approval_id)
            assert '"decision": "approved"' in signal.value
            events = await service.list_events(
                bootstrap.tenant_id,
                principal("reviewer"),
                created.summary.run_id,
                0,
                20,
            )
            assert [event.event_type for event in events].count(
                "human.approval.submitted"
            ) == 1
        finally:
            await transaction.rollback()
    await engine.dispose()


@pytest.mark.database
@pytest.mark.anyio
async def test_runtime_failure_projection_is_terminal_audited_and_idempotent() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        sessions = async_sessionmaker(
            connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        temporal = TemporalGateway()
        try:
            async with sessions.begin() as session:
                bootstrap = await bootstrap_local_mvp(
                    session,
                    slug=f"local-runtime-failure-{uuid4()}",
                    developer=principal("developer"),
                    reviewer=principal("reviewer"),
                )
            service = PostgresRunService(sessions, temporal, profile="local_mvp")
            created = await service.create_run(
                bootstrap.tenant_id,
                principal("developer"),
                input_request(),
                "runtime-failure-projection-001",
            )
            identity = temporal.started[0].identity
            projection = PostgresRunProjection(sessions)
            reason = "irreversible:clarifier:StructuredReasoningError"

            first = await projection.project_runtime_failure(
                tenant_id=bootstrap.tenant_id,
                run_id=created.summary.run_id,
                trace_id=UUID(identity.trace_id),
                reason=reason,
            )
            second = await projection.project_runtime_failure(
                tenant_id=bootstrap.tenant_id,
                run_id=created.summary.run_id,
                trace_id=UUID(identity.trace_id),
                reason=reason,
            )
            detail = await service.get_run(
                bootstrap.tenant_id, principal("developer"), created.summary.run_id
            )
            events = await service.list_events(
                bootstrap.tenant_id,
                principal("developer"),
                created.summary.run_id,
                0,
                20,
            )

            assert first == second == f"run:{created.summary.run_id}:failed"
            assert detail.summary.status == "failed"
            assert any(
                step["name"] == "clarifier" and step["status"] == "failed"
                for step in detail.steps
            )
            failure = next(item for item in detail.artifacts if item["kind"] == "failure")
            assert failure["payload"]["reason"] == reason
            assert detail.evaluation is not None
            assert detail.evaluation["outcome"] == "failed"
            assert detail.evaluation["detail"]["failure_reason"] == reason
            assert [event.event_type for event in events].count("run.failed") == 1
            assert sum(item["action"] == "runtime_fail" for item in detail.audit) == 1
        finally:
            await transaction.rollback()
    await engine.dispose()
