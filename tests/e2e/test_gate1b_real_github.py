"""Protected manual test for the real GitHub side effect at the Gate 1B boundary."""

from datetime import datetime, timezone
import os
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aegisflow_core.control_plane.approvals import (
    PostgresApprovalAuthorizer,
    PostgresApprovalGateway,
)
from aegisflow_core.control_plane.domain import Run, Step, Tenant, Workflow
from aegisflow_core.control_plane.idempotency_ledger import IdempotencyLedger
from aegisflow_core.gateway.github.auth import InstallationTokenProvider
from aegisflow_core.gateway.github.idempotency_guard import PostgresIdempotencyGuard
from aegisflow_core.gateway.github.pull_request import (
    FileChange,
    GitHubWriteClient,
    WriteAuthorization,
    create_draft_pull_request,
    draft_pr_action_preview,
    digest_action_preview,
    digest_file_changes,
)
from aegisflow_core.gateway.github.read_tools import GitHubReadClient
from aegisflow_core.gateway.policy.gate import RepositoryTarget
from aegisflow_core.packs.delivery.contracts.determinism import SystemClock
from aegisflow_core.packs.delivery.contracts.review_decision import ReviewFinding


def test_gate1b_workflow_maps_github_safe_environment_names() -> None:
    """GitHub rejects variable and secret names that start with ``GITHUB_``."""
    workflow = (
        Path(__file__).parents[2] / ".github" / "workflows" / "gate1b-e2e.yml"
    ).read_text(encoding="utf-8")

    assert "vars.AEGISFLOW_GITHUB_APP_ID" in workflow
    assert "vars.AEGISFLOW_GITHUB_APP_INSTALLATION_ID" in workflow
    assert "secrets.AEGISFLOW_APP_PRIVATE_KEY" in workflow
    assert "secrets.AEGISFLOW_APP_WEBHOOK_SECRET" in workflow


@pytest.mark.real_github
@pytest.mark.asyncio
async def test_real_github_draft_pr_is_deduplicated_and_marker_cleaned() -> None:
    required = {
        name: os.environ.get(name)
        for name in (
            "DATABASE_URL", "GITHUB_APP_ID", "GITHUB_APP_INSTALLATION_ID",
            "GITHUB_APP_PRIVATE_KEY", "GITHUB_APP_WEBHOOK_SECRET",
            "AEGISFLOW_TEST_REPOSITORY", "AEGISFLOW_BOOTSTRAP_TENANT_SLUG",
        )
    }
    missing = sorted(name for name, value in required.items() if not value)
    if missing:
        pytest.skip("protected Gate 1B environment is not configured")
    repository = required["AEGISFLOW_TEST_REPOSITORY"] or ""
    owner, repo = repository.split("/", 1)
    target = RepositoryTarget(owner, repo)
    run_id, tenant_id, workflow_id, step_id = uuid4(), uuid4(), uuid4(), uuid4()
    branch = f"aegisflow/run-{run_id}"
    pr_number: int | None = None

    provider = InstallationTokenProvider(
        app_id=required["GITHUB_APP_ID"] or "",
        private_key_pem=required["GITHUB_APP_PRIVATE_KEY"] or "",
        installation_id=required["GITHUB_APP_INSTALLATION_ID"] or "",
        clock=SystemClock(),
    )
    http = httpx.AsyncClient(timeout=10)
    read_client = GitHubReadClient(token_provider=provider, http_client=http)
    write_client = GitHubWriteClient(token_provider=provider, http_client=http)
    engine = create_async_engine(required["DATABASE_URL"] or "")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        token = await provider.get_token()
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        ref = await http.get(
            f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/main",
            headers=headers,
        )
        ref.raise_for_status()
        base_sha = str(ref.json()["object"]["sha"])

        async with sessions.begin() as session:
            session.add(Tenant(
                id=tenant_id, slug=f"gate1b-e2e-{tenant_id.hex}", name="Gate 1B E2E"
            ))
            await session.flush()
            session.add(Workflow(
                id=workflow_id, tenant_id=tenant_id, name="gate1b", version=1,
                definition_hash="gate1b-e2e", status="active",
            ))
            await session.flush()
            session.add(Run(
                id=run_id, tenant_id=tenant_id, workflow_id=workflow_id,
                workflow_version=1, status="waiting_approval",
            ))
            await session.flush()
            session.add(Step(
                id=step_id, tenant_id=tenant_id, run_id=run_id,
                name="reviewer", sequence=7, status="completed",
                completed_at=datetime.now(timezone.utc),
            ))

        changes = (FileChange(
            path=f"aegisflow-e2e/{run_id}.txt", operation="add",
            content=f"AegisFlow Gate 1B E2E {run_id}\n".encode(),
        ),)
        preview = draft_pr_action_preview(
            effect_mode="github",
            target=target,
            base_ref="main",
            base_sha=base_sha,
            branch_name=f"aegisflow/run-{run_id}",
            changes=changes,
            risk="L3",
        )
        action_digest = digest_action_preview(preview)
        approval_gateway = PostgresApprovalGateway(sessions)
        approval_id = await approval_gateway.request_approval(
            tenant_id, run_id, step_id,
            [ReviewFinding(severity="info", message="protected manual E2E")],
            action_preview=preview,
            action_digest=action_digest,
        )
        await approval_gateway.submit_decision(
            approval_id, run_id, "approved", "protected-environment"
        )
        authorization = WriteAuthorization(
            approval_id=approval_id, tenant_id=tenant_id, run_id=run_id,
            step_id=step_id, repository_target=target, base_ref="main",
            base_sha=base_sha,
            content_digest=digest_file_changes(changes),
            action_digest=action_digest, effect_mode="github", risk="L3",
        )
        guard = PostgresIdempotencyGuard(
            IdempotencyLedger(sessions, SystemClock())
        )
        arguments = dict(
            github_client=write_client, read_client=read_client, changes=changes,
            authorization=authorization,
            approval_authorizer=PostgresApprovalAuthorizer(sessions),
            idempotency_guard=guard,
        )
        first = await create_draft_pull_request(**arguments)
        second = await create_draft_pull_request(**arguments)
        pr_number = first.pull_request_number
        assert second.pull_request_number == pr_number
        assert second.reused_existing
    finally:
        if pr_number is not None:
            token = await provider.get_token()
            headers = {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token.token}",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            close_response = await http.patch(
                f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}",
                headers=headers, json={"state": "closed"},
            )
            close_response.raise_for_status()
        token = await provider.get_token()
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        delete_response = await http.delete(
            f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch}",
            headers=headers,
        )
        if delete_response.status_code not in (204, 404):
            delete_response.raise_for_status()
        await read_client.aclose()
        await write_client.aclose()
        await http.aclose()
        await engine.dispose()
