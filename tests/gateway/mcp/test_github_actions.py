from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import httpx
import pytest

from aegisflow_core.gateway import mcp
from aegisflow_core.control_plane.rbac import Capability
from aegisflow_core.gateway.github.auth import InstallationToken
from aegisflow_core.gateway.github.read_tools import ActionsRunSnapshot, GitHubReadClient
from aegisflow_core.gateway.mcp.github_actions import GitHubActionsReadAdapter
from aegisflow_core.gateway.mcp.gate import InvocationRequest, McpInvocationGate
from aegisflow_core.gateway.policy.contextual import PolicyInput
from aegisflow_core.packs.delivery.contracts.idempotency import Execute


class TokenProvider:
    async def get_token(self) -> InstallationToken:
        return InstallationToken(token="fixture-token", expires_at=datetime.now(timezone.utc) + timedelta(hours=1))


@pytest.mark.anyio
async def test_actions_client_uses_get_and_bounds_metadata_without_logs_or_downloads() -> None:
    requests: list[httpx.Request] = []
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request); path = request.url.path
        if path.endswith("/runs/42"):
            return httpx.Response(200, json={"id": 42, "name": "CI", "status": "completed", "conclusion": "success", "head_sha": "a" * 40, "html_url": "https://github.test/o/r/actions/runs/42"})
        if path.endswith("/jobs"):
            return httpx.Response(200, json={"jobs": [
                {"id": 1, "name": "test", "status": "completed", "conclusion": "success", "html_url": "https://github.test/jobs/1"},
                {"id": 2, "name": "extra", "status": "completed", "conclusion": "success", "html_url": "https://github.test/jobs/2"},
            ]})
        return httpx.Response(200, json={"artifacts": [{"id": 3, "name": "junit", "size_in_bytes": 123, "expired": False, "archive_download_url": "must-not-leak"}]})
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = GitHubReadClient(token_provider=TokenProvider(), http_client=http_client, api_base_url="https://api.github.test")
    try: result = await client.read_actions_run("o", "r", 42, max_items=1)
    finally: await http_client.aclose()
    assert result.truncated is True and [job.name for job in result.jobs] == ["test"]
    assert result.artifacts[0].name == "junit"
    assert "download" not in result.model_dump_json()
    assert all(request.method == "GET" for request in requests)
    assert all("logs" not in request.url.path and "artifacts/3" not in request.url.path for request in requests)


class FakeActionsClient:
    async def read_actions_run(self, owner: str, repo: str, run_id: int, max_items: int) -> ActionsRunSnapshot:
        assert (owner, repo, run_id, max_items) == ("KinguYume-G", "AegisFlow", 42, 10)
        return ActionsRunSnapshot(id=42, name="CI", status="completed", conclusion="success", head_sha="b" * 40,
                                  html_url="https://github.test/run/42", jobs=[], artifacts=[], truncated=False)


class Registration:
    canonical_name = "github_actions_run_read"; version = "1.0.0"
    adapter_identifier = GitHubActionsReadAdapter.identifier
    input_schema_hash = GitHubActionsReadAdapter.input_schema_hash
    output_schema_hash = GitHubActionsReadAdapter.output_schema_hash
    allowed_scopes = ["actions:read"]; risk_level = "L1"
    def __init__(self, tenant_id: UUID) -> None: self.tenant_id = tenant_id


class Registry:
    def __init__(self, registration: Registration) -> None: self.registration = registration
    async def get_active(self, tenant_id: UUID, name: str, version: str) -> Registration | None:
        return self.registration if (tenant_id, name, version) == (self.registration.tenant_id, self.registration.canonical_name, self.registration.version) else None


class Resolver:
    async def resolve(self, adapter_identifier: str) -> object:
        assert adapter_identifier == GitHubActionsReadAdapter.identifier; return object()


class Audit:
    def __init__(self) -> None: self.records: list[dict[str, object]] = []
    async def record(self, **fields: object) -> None: self.records.append(fields)


class Ledger:
    def __init__(self) -> None: self.claim = uuid4(); self.completed = False
    async def begin(self, _command: object) -> Execute: return Execute(self.claim)
    async def complete(self, claim_token: UUID, _reference: str) -> None:
        assert claim_token == self.claim; self.completed = True
    async def fail(self, *_args: object) -> None: raise AssertionError("unexpected failure")


class Approval:
    async def approved_by(self, **_fields: object) -> None: return None


@pytest.mark.anyio
async def test_actions_adapter_runs_through_scope_policy_idempotency_and_audit() -> None:
    tenant_id = uuid4(); registration = Registration(tenant_id); audit = Audit(); ledger = Ledger()
    adapter = GitHubActionsReadAdapter(lambda _credentials: FakeActionsClient())  # type: ignore[arg-type]
    gate = McpInvocationGate(registry=Registry(registration), adapters={adapter.identifier: adapter},
                             credential_resolver=Resolver(), audit=audit, idempotency=ledger, approval_verifier=Approval())
    policy = PolicyInput(tenant_id=tenant_id, membership_active=True,
        capabilities=frozenset({Capability.TOOL_INVOKE}), required_capability=Capability.TOOL_INVOKE,
        repository="KinguYume-G/AegisFlow", allowed_repositories=frozenset({"KinguYume-G/AegisFlow"}),
        environment="development", allowed_environments=frozenset({"development"}), tool_registered=True,
        registered_scopes=frozenset({"actions:read"}), requested_scope="actions:read", risk_level="L1",
        max_risk_level="L1", injection_severity="none", approval_required=False, approval_granted=False,
        request_actor="issuer|developer", approval_actor=None)
    result = await gate.invoke(InvocationRequest(tenant_id=tenant_id, run_id=uuid4(), step_id=uuid4(),
        tool_name="github_actions_run_read", tool_version="1.0.0", requested_scope="actions:read",
        arguments={"owner": "KinguYume-G", "repository": "AegisFlow", "run_id": 42, "max_items": 10},
        untrusted_content=(), policy_input=policy, trace_id="trace-actions", idempotency_key="actions-42"))
    assert result["id"] == 42 and ledger.completed is True
    assert audit.records[-1]["decision"] == "allow"


def test_actions_adapter_rejects_unknown_or_write_shaped_input() -> None:
    adapter = GitHubActionsReadAdapter()
    assert adapter.validate_input({"owner": "o", "repository": "r", "run_id": 1})
    assert not adapter.validate_input({"owner": "o", "repository": "r", "run_id": 1, "rerun": True})


def test_mcp_package_preserves_existing_public_exports() -> None:
    assert {
        "ApprovalRequiredError",
        "GitHubActionsReadAdapter",
        "InvocationRequest",
        "McpInvocationGate",
        "ReusedInvocation",
    } <= set(mcp.__all__)
