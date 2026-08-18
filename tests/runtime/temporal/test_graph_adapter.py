from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aegisflow_core.gateway.sandbox.runner import (
    InMemorySandboxRunner,
    SandboxResult,
)
from aegisflow_core.models.contracts import ModelRequest, ModelResponse, RouteAttempt
from aegisflow_core.runtime.checkpoint import PostgresCheckpointManager
from aegisflow_core.runtime.temporal.contracts import (
    AdvanceRequest,
    HumanSignal,
    RuntimeIdentity,
)
from aegisflow_core.runtime.temporal.graph_adapter import (
    CHECKPOINT_ALLOWED_TYPES,
    PostgresDeliveryGraphAdapter,
    _prepare_workspace,
    _resume_payload,
)
from aegisflow_core.runtime.tracing import unavailable_cost_usage, unavailable_token_usage
from aegisflow_core.settings import Settings


class ScriptedModelGateway:
    async def complete(self, request: ModelRequest) -> ModelResponse:
        system = request.messages[0].content
        if "Clarifier" in system:
            content = '{"is_sufficient":true,"questions":[]}'
        elif "Planner" in system:
            content = json.dumps(
                {
                    "summary": "Implement and verify the local fixture.",
                    "risk_level": "L2",
                    "tasks": [
                        {
                            "description": "Read, implement, test, and prepare a candidate.",
                            "required_tools": [
                                "repository_read",
                                "repository_write",
                                "test_execute",
                                "sandbox_execute",
                                "pull_request_write",
                            ],
                        }
                    ],
                }
            )
        elif "Executor" in system:
            content = json.dumps(
                {
                    "files": {
                        "app.py": (
                            '"""Controlled local MVP fixture."""\n\n'
                            "def deliverable() -> str:\n"
                            '    return "implemented"\n'
                        )
                    }
                }
            )
        elif "Reviewer" in system:
            content = json.dumps(
                {"findings": [{"severity": "info", "message": "Tests passed."}]}
            )
        else:
            raise AssertionError(system)
        return ModelResponse(
            content=content,
            resolved_model="ollama_chat/qwen3:8b",
            token_usage=unavailable_token_usage(),
            cost=unavailable_cost_usage(),
            latency_ms=1.0,
            route_chain=(
                RouteAttempt("local_ollama", "ollama_chat/qwen3:8b", "succeeded"),
            ),
        )


def _settings(database_url: str, workspace: Path) -> Settings:
    return Settings(
        app_env="test",
        app_base_url="http://127.0.0.1:8000",
        database_url=database_url,
        sandbox_broker_url="http://sandbox.invalid",
        langgraph_database_url=database_url,
        local_mvp_profile_enabled=True,
        local_mvp_developer_token="developer-token-placeholder",
        local_mvp_reviewer_token="reviewer-token-placeholder",
        local_mvp_workspace_root=str(workspace.resolve()),
        local_mvp_github_dry_run=True,
        model_ollama_enabled=True,
        model_ollama_name="qwen3:8b",
        model_ollama_api_key_env="OLLAMA_API_KEY",
        model_ollama_base_url="http://127.0.0.1:11434",
    )


def test_signal_resume_payload_is_exactly_bound_to_pending_target() -> None:
    tenant, run = uuid4(), uuid4()
    signal = HumanSignal(
        "signal-1",
        "approval",
        str(tenant),
        str(run),
        "approval-1",
        '{"decision":"approved","reason":null}',
        "local:reviewer",
        "2026-08-17T00:00:00Z",
    )
    assert _resume_payload(signal, {"approval_id": "approval-1"}) == {
        "decision": "approved",
        "decided_by": "local:reviewer",
        "reason": None,
    }
    with pytest.raises(PermissionError):
        _resume_payload(signal, {"approval_id": "another-approval"})


def test_workspace_seed_is_bounded_and_does_not_overwrite_existing_work(
    tmp_path: Path,
) -> None:
    tenant, run = uuid4(), uuid4()
    request = SimpleNamespace(title="Fixture", body="Implement a safe local fixture.")
    workspace = _prepare_workspace(tmp_path, tenant, run, request)
    (workspace / "app.py").write_text("preserve\n", encoding="utf-8")
    assert _prepare_workspace(tmp_path, tenant, run, request) == workspace
    assert (workspace / "app.py").read_text(encoding="utf-8") == "preserve\n"
    assert (workspace / "tests" / "test_app.py").is_file()


@pytest.mark.database
@pytest.mark.asyncio
async def test_postgres_adapter_reconstructs_wait_and_completes_dry_run(
    tmp_path: Path,
) -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    tenant, workflow, run, trace = uuid4(), uuid4(), uuid4(), uuid4()
    identity = RuntimeIdentity(str(tenant), str(run), str(trace), 1)
    async with engine.begin() as connection:
        await connection.execute(
            text("INSERT INTO tenants (id,slug,name) VALUES (:id,:slug,'Adapter Test')"),
            {"id": tenant, "slug": f"adapter-{tenant.hex}"},
        )
        await connection.execute(
            text(
                "INSERT INTO workflows (id,tenant_id,name,version,definition_hash) "
                "VALUES (:id,:tenant,'delivery',1,'hash')"
            ),
            {"id": workflow, "tenant": tenant},
        )
        await connection.execute(
            text(
                "INSERT INTO runs (id,tenant_id,workflow_id,workflow_version,status) "
                "VALUES (:id,:tenant,:workflow,1,'running')"
            ),
            {"id": run, "tenant": tenant, "workflow": workflow},
        )
        await connection.execute(
            text(
                "INSERT INTO run_requests "
                "(tenant_id,run_id,source_type,title,body,repository_owner,"
                "repository_name,base_ref,base_sha,requested_by,idempotency_key,"
                "input_hash,trace_id,temporal_workflow_id) VALUES "
                "(:tenant,:run,'prd','Implement fixture',:body,'owner','fixture',"
                "'main',:sha,'local:developer','adapter-key',:hash,:trace,:temporal)"
            ),
            {
                "tenant": tenant,
                "run": run,
                "body": "Implement the controlled fixture and verify the unit test.",
                "sha": "a" * 40,
                "hash": "b" * 64,
                "trace": trace,
                "temporal": identity.temporal_workflow_id,
            },
        )

    manager = PostgresCheckpointManager(
        database_url, allowed_types=CHECKPOINT_ALLOWED_TYPES
    )
    await manager.setup()
    sandbox = InMemorySandboxRunner(
        SandboxResult(
            status="completed",
            exit_code=0,
            stdout="1 test passed",
            stderr="",
            duration_ms=1,
            workspace_output=tmp_path,
        )
    )
    adapter = PostgresDeliveryGraphAdapter(
        settings=_settings(database_url, tmp_path / "workspaces"),
        session_factory=sessions,
        checkpoint_manager=manager,
        model_gateway=ScriptedModelGateway(),  # type: ignore[arg-type]
        sandbox_runner=sandbox,
    )

    waiting = await adapter.advance(AdvanceRequest(identity))
    assert waiting.status == "waiting_approval"
    assert waiting.wait_reference

    reconstructed = PostgresDeliveryGraphAdapter(
        settings=_settings(database_url, tmp_path / "workspaces"),
        session_factory=sessions,
        checkpoint_manager=manager,
        model_gateway=ScriptedModelGateway(),  # type: ignore[arg-type]
        sandbox_runner=sandbox,
    )
    assert await reconstructed.advance(AdvanceRequest(identity)) == waiting

    completed = await reconstructed.advance(
        AdvanceRequest(
            identity,
            HumanSignal(
                "approval-signal",
                "approval",
                str(tenant),
                str(run),
                waiting.wait_reference,
                '{"decision":"approved","reason":"reviewed"}',
                "local:reviewer",
                "2026-08-17T00:00:00Z",
            ),
        )
    )
    assert completed.status == "completed"
    assert completed.result_reference == f"aegisflow://draft-pr-candidates/{run}"

    async with engine.connect() as connection:
        facts = (
            await connection.execute(
                text(
                    "SELECT r.status, a.decision, a.decided_by, e.task_success, "
                    "e.total_steps, e.completed_steps FROM runs r "
                    "JOIN approvals a ON a.tenant_id=r.tenant_id AND a.run_id=r.id "
                    "JOIN run_evaluations e ON e.tenant_id=r.tenant_id AND e.run_id=r.id "
                    "WHERE r.tenant_id=:tenant AND r.id=:run"
                ),
                {"tenant": tenant, "run": run},
            )
        ).mappings().one()
        artifact_kinds = set(
            (
                await connection.execute(
                    text(
                        "SELECT kind FROM run_artifacts "
                        "WHERE tenant_id=:tenant AND run_id=:run"
                    ),
                    {"tenant": tenant, "run": run},
                )
            ).scalars()
        )
    assert facts["status"] == "completed"
    assert facts["decision"] == "approved"
    assert facts["decided_by"] == "local:reviewer"
    assert facts["task_success"] is True
    assert facts["total_steps"] == facts["completed_steps"] == 10
    assert artifact_kinds == {
        "context",
        "plan",
        "sandbox",
        "diff",
        "draft_pr_candidate",
    }
    await engine.dispose()
