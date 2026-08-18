"""Authorized, idempotent GitHub draft pull-request creation."""

from __future__ import annotations

import base64
from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Literal, Protocol
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

from aegisflow_core.gateway.github.auth import InstallationTokenProvider
from aegisflow_core.gateway.github.read_tools import (
    GitHubPermissionDeniedError,
    GitHubRateLimitedError,
    GitHubResourceNotFoundError,
    GitHubTimeoutError,
    GitHubUpstreamError,
    PullRequestSnapshot,
)
from aegisflow_core.gateway.policy.gate import RepositoryTarget
from aegisflow_core.packs.delivery.contracts.idempotency import (
    ClaimResult,
    Execute,
    FinalFailure,
    IdempotentCommand,
    InProgress,
    Reuse,
)
from aegisflow_core.packs.delivery.contracts.action_approval import (
    digest_action_preview,
)


class FileChange(BaseModel):
    """One bounded repository-relative file mutation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=1, max_length=1024)
    operation: Literal["add", "update", "delete"]
    content: bytes | None = Field(default=None, max_length=1_000_000)

    @model_validator(mode="after")
    def validate_operation(self) -> FileChange:
        parts = self.path.replace("\\", "/").split("/")
        if self.path.startswith(("/", "\\")) or any(
            part in {"", ".", ".."} for part in parts
        ):
            raise ValueError("path must be a normalized repository-relative path")
        if self.operation == "delete" and self.content is not None:
            raise ValueError("delete changes cannot contain content")
        if self.operation != "delete" and self.content is None:
            raise ValueError("add and update changes require content")
        return self


class WriteAuthorization(BaseModel):
    """Human approval bound to the exact write scope and content."""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    approval_id: UUID
    tenant_id: UUID
    run_id: UUID
    step_id: UUID
    repository_target: RepositoryTarget
    base_ref: str = Field(min_length=1, max_length=255)
    base_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    effect_mode: Literal["github", "dry_run"]
    risk: Literal["L1", "L2", "L3"]


class DraftPullRequestResult(BaseModel):
    """Stable result suitable for ledger persistence and reconciliation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    effect_mode: Literal["github", "dry_run"] = "github"
    pull_request_url: str | None
    pull_request_number: int | None = Field(default=None, gt=0)
    candidate_reference: str | None = None
    branch_name: str
    commit_sha: str | None = None
    reused_existing: bool

    @model_validator(mode="after")
    def validate_effect_result(self) -> DraftPullRequestResult:
        if self.effect_mode == "github":
            if self.pull_request_url is None or self.pull_request_number is None:
                raise ValueError("GitHub results require a pull request URL and number")
            if self.candidate_reference is not None:
                raise ValueError("GitHub results cannot contain a dry-run candidate reference")
        elif (
            self.pull_request_url is not None
            or self.pull_request_number is not None
            or self.candidate_reference is None
        ):
            raise ValueError("dry-run results require only a candidate reference")
        return self


class MissingApprovalError(RuntimeError):
    """No database-backed approval authorized the exact write."""


class IdempotencyInProgressError(RuntimeError):
    def __init__(self, retry_after_seconds: float) -> None:
        super().__init__("an identical GitHub write is already in progress")
        self.retry_after_seconds = retry_after_seconds


class IdempotencyFinalFailureError(RuntimeError):
    """An identical command reached a non-retryable terminal failure."""


class ApprovalAuthorizer(Protocol):
    async def verify(
        self,
        authorization: WriteAuthorization,
        actual_content_digest: str,
        actual_action_digest: str,
    ) -> None: ...


class IdempotencyGuard(Protocol):
    async def begin(self, command: IdempotentCommand) -> ClaimResult: ...

    async def complete(
        self, claim_token: UUID, result_reference: str
    ) -> None: ...

    async def fail(
        self, claim_token: UUID, retryable: bool, reason: str
    ) -> None: ...


class GitHubReadReconciler(Protocol):
    async def find_pull_request_by_head_or_marker(
        self, owner: str, repo: str, head_ref: str, marker: str, max_items: int = 200
    ) -> PullRequestSnapshot | None: ...


@dataclass(frozen=True, slots=True)
class CreatedCommit:
    sha: str


class GitHubWritePort(Protocol):
    async def create_commit_from_changes(
        self,
        *,
        target: RepositoryTarget,
        expected_base_sha: str,
        branch_name: str,
        changes: tuple[FileChange, ...],
        author: dict[str, str],
    ) -> CreatedCommit: ...

    async def open_draft_pull_request(
        self,
        *,
        target: RepositoryTarget,
        branch_name: str,
        base_ref: str,
        title: str,
        body: str,
    ) -> PullRequestSnapshot: ...


def digest_file_changes(changes: Sequence[FileChange]) -> str:
    """Hash a canonical, order-independent representation of exact bytes."""
    canonical = [
        {
            "path": change.path,
            "operation": change.operation,
            "content_sha256": (
                sha256(change.content).hexdigest() if change.content is not None else None
            ),
        }
        for change in sorted(changes, key=lambda item: item.path)
    ]
    return sha256(
        json.dumps(canonical, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()


def draft_pr_action_preview(
    *,
    effect_mode: Literal["github", "dry_run"],
    target: RepositoryTarget,
    base_ref: str,
    base_sha: str,
    branch_name: str,
    changes: Sequence[FileChange],
    risk: Literal["L1", "L2", "L3"],
) -> dict[str, object]:
    return {
        "effect": (
            "create_draft_pr_candidate"
            if effect_mode == "dry_run"
            else "create_github_draft_pr"
        ),
        "effect_mode": effect_mode,
        "repository": target.full_name,
        "base_ref": base_ref,
        "base_sha": base_sha,
        "branch_name": branch_name,
        "changed_files": [change.path for change in changes],
        "content_digest": digest_file_changes(changes),
        "risk": risk,
    }


def _verify_exact_action(
    authorization: WriteAuthorization,
    changes: Sequence[FileChange],
    *,
    required_effect_mode: Literal["github", "dry_run"],
    base_ref: str,
) -> tuple[str, str]:
    if authorization.effect_mode != required_effect_mode or authorization.base_ref != base_ref:
        raise MissingApprovalError("write authorization effect or base ref mismatch")
    actual_content_digest = digest_file_changes(changes)
    preview = draft_pr_action_preview(
        effect_mode=required_effect_mode,
        target=authorization.repository_target,
        base_ref=base_ref,
        base_sha=authorization.base_sha,
        branch_name=f"aegisflow/run-{authorization.run_id}",
        changes=changes,
        risk=authorization.risk,
    )
    return actual_content_digest, digest_action_preview(preview)


def marker_for(command: IdempotentCommand) -> str:
    return (
        "<!-- aegisflow:marker "
        f"run_id={command.run_id} idempotency_key={command.idempotency_key} -->"
    )


async def create_draft_pull_request(
    *,
    github_client: GitHubWritePort,
    read_client: GitHubReadReconciler,
    changes: tuple[FileChange, ...],
    authorization: WriteAuthorization,
    approval_authorizer: ApprovalAuthorizer,
    idempotency_guard: IdempotencyGuard,
    base_ref: str | None = None,
) -> DraftPullRequestResult:
    """Create exactly one draft PR after exact-scope human authorization."""
    if not changes or len({change.path for change in changes}) != len(changes):
        raise ValueError("changes must be non-empty with unique paths")
    resolved_base_ref = base_ref or authorization.base_ref
    actual_digest, actual_action_digest = _verify_exact_action(
        authorization,
        changes,
        required_effect_mode="github",
        base_ref=resolved_base_ref,
    )
    try:
        await approval_authorizer.verify(
            authorization, actual_digest, actual_action_digest
        )
    except Exception:
        raise MissingApprovalError("write authorization was not verified") from None
    if actual_digest != authorization.content_digest:
        raise MissingApprovalError("write authorization content digest mismatch")

    arguments_hash = sha256(
        (
            f"{authorization.repository_target.full_name}\0{authorization.base_sha}\0"
            f"{actual_digest}"
        ).encode()
    ).hexdigest()
    key = sha256(
        f"tool_call\0{authorization.tenant_id}\0{authorization.run_id}\0"
        f"{authorization.step_id}\0github.create_draft_pr\0{arguments_hash}".encode()
    ).hexdigest()
    command = IdempotentCommand(
        scope="tool_call",
        idempotency_key=key,
        arguments_hash=arguments_hash,
        tenant_id=authorization.tenant_id,
        run_id=authorization.run_id,
        step_id=authorization.step_id,
        tool_name="github.create_draft_pr",
    )
    claim = await idempotency_guard.begin(command)
    if isinstance(claim, Reuse):
        return _decode_result_reference(claim.result_reference, reused=True)
    if isinstance(claim, InProgress):
        raise IdempotencyInProgressError(claim.retry_after_seconds)
    if isinstance(claim, FinalFailure):
        raise IdempotencyFinalFailureError(claim.reason)

    branch_name = f"aegisflow/run-{authorization.run_id}"
    marker = marker_for(command)
    try:
        existing = await read_client.find_pull_request_by_head_or_marker(
            authorization.repository_target.owner,
            authorization.repository_target.repository,
            branch_name,
            marker,
        )
        if existing is not None:
            result = _from_snapshot(
                existing,
                authorization.repository_target,
                branch_name,
                reused=True,
            )
            await idempotency_guard.complete(
                claim.claim_token, _encode_result_reference(result)
            )
            return result

        commit = await github_client.create_commit_from_changes(
            target=authorization.repository_target,
            expected_base_sha=authorization.base_sha,
            branch_name=branch_name,
            changes=changes,
            author={"name": "AegisFlow Bot", "email": "aegisflow-bot@users.noreply.github.com"},
        )
        snapshot = await github_client.open_draft_pull_request(
            target=authorization.repository_target,
            branch_name=branch_name,
            base_ref=resolved_base_ref,
            title=f"AegisFlow draft for run {authorization.run_id}",
            body=marker,
        )
        result = _from_snapshot(
            snapshot,
            authorization.repository_target,
            branch_name,
            reused=False,
            commit_sha=commit.sha,
        )
        await idempotency_guard.complete(
            claim.claim_token, _encode_result_reference(result)
        )
        return result
    except Exception as exc:
        await idempotency_guard.fail(
            claim.claim_token,
            not isinstance(exc, (MissingApprovalError, ValueError)),
            type(exc).__name__,
        )
        raise


async def create_draft_pull_request_candidate(
    *,
    github_client: GitHubWritePort,
    read_client: GitHubReadReconciler,
    changes: tuple[FileChange, ...],
    authorization: WriteAuthorization,
    approval_authorizer: ApprovalAuthorizer,
    idempotency_guard: IdempotencyGuard,
    base_ref: str | None = None,
) -> DraftPullRequestResult:
    """Persist an approved, idempotent candidate without a GitHub side effect."""
    del github_client, read_client
    if not changes or len({change.path for change in changes}) != len(changes):
        raise ValueError("changes must be non-empty with unique paths")
    resolved_base_ref = base_ref or authorization.base_ref
    actual_digest, actual_action_digest = _verify_exact_action(
        authorization,
        changes,
        required_effect_mode="dry_run",
        base_ref=resolved_base_ref,
    )
    try:
        await approval_authorizer.verify(
            authorization, actual_digest, actual_action_digest
        )
    except Exception:
        raise MissingApprovalError("write authorization was not verified") from None
    if actual_digest != authorization.content_digest:
        raise MissingApprovalError("write authorization content digest mismatch")
    if actual_action_digest != authorization.action_digest:
        raise MissingApprovalError("write authorization action digest mismatch")
    if actual_action_digest != authorization.action_digest:
        raise MissingApprovalError("write authorization action digest mismatch")

    arguments_hash = sha256(
        (
            f"{authorization.repository_target.full_name}\0{authorization.base_sha}\0"
            f"{actual_digest}"
        ).encode()
    ).hexdigest()
    key = sha256(
        f"tool_call\0{authorization.tenant_id}\0{authorization.run_id}\0"
        f"{authorization.step_id}\0github.create_draft_pr_candidate\0{arguments_hash}".encode()
    ).hexdigest()
    command = IdempotentCommand(
        scope="tool_call",
        idempotency_key=key,
        arguments_hash=arguments_hash,
        tenant_id=authorization.tenant_id,
        run_id=authorization.run_id,
        step_id=authorization.step_id,
        tool_name="github.create_draft_pr_candidate",
    )
    claim = await idempotency_guard.begin(command)
    if isinstance(claim, Reuse):
        result = _decode_result_reference(claim.result_reference, reused=True)
        if result.effect_mode != "dry_run":
            raise IdempotencyFinalFailureError(
                "candidate ledger contained a remote GitHub result"
            )
        return result
    if isinstance(claim, InProgress):
        raise IdempotencyInProgressError(claim.retry_after_seconds)
    if isinstance(claim, FinalFailure):
        raise IdempotencyFinalFailureError(claim.reason)

    result = DraftPullRequestResult(
        effect_mode="dry_run",
        pull_request_url=None,
        pull_request_number=None,
        candidate_reference=f"aegisflow://draft-pr-candidates/{authorization.run_id}",
        branch_name=f"aegisflow/run-{authorization.run_id}",
        reused_existing=False,
    )
    await idempotency_guard.complete(
        claim.claim_token, _encode_result_reference(result)
    )
    return result


def _from_snapshot(
    snapshot: PullRequestSnapshot,
    target: RepositoryTarget,
    branch_name: str,
    *,
    reused: bool,
    commit_sha: str | None = None,
) -> DraftPullRequestResult:
    return DraftPullRequestResult(
        effect_mode="github",
        pull_request_url=(
            f"https://github.com/{target.owner}/{target.repository}/pull/{snapshot.number}"
        ),
        pull_request_number=snapshot.number,
        branch_name=branch_name,
        commit_sha=commit_sha,
        reused_existing=reused,
    )


def _encode_result_reference(result: DraftPullRequestResult) -> str:
    return result.model_dump_json()


def _decode_result_reference(value: str, *, reused: bool) -> DraftPullRequestResult:
    parsed = DraftPullRequestResult.model_validate_json(value)
    return parsed.model_copy(update={"reused_existing": reused})


class GitHubWriteClient:
    """Narrow async Git Data and draft-PR API adapter."""

    def __init__(
        self,
        *,
        token_provider: InstallationTokenProvider,
        timeout_seconds: float = 10.0,
        http_client: httpx.AsyncClient | None = None,
        api_base_url: str = "https://api.github.com",
    ) -> None:
        self._token_provider = token_provider
        self._timeout = timeout_seconds
        self._client = http_client or httpx.AsyncClient(timeout=timeout_seconds)
        self._owns_client = http_client is None
        self._base = api_base_url.rstrip("/")

    async def create_commit_from_changes(
        self,
        *,
        target: RepositoryTarget,
        expected_base_sha: str,
        branch_name: str,
        changes: tuple[FileChange, ...],
        author: dict[str, str],
    ) -> CreatedCommit:
        prefix = f"/repos/{target.owner}/{target.repository}/git"
        try:
            existing_ref = await self._request(
                "GET", f"{prefix}/ref/heads/{branch_name}"
            )
        except GitHubResourceNotFoundError:
            existing_ref = None
        if existing_ref is not None:
            try:
                return CreatedCommit(sha=str(existing_ref["object"]["sha"]))
            except (KeyError, TypeError):
                raise GitHubUpstreamError("GitHub branch response was malformed") from None
        base_commit = await self._request("GET", f"{prefix}/commits/{expected_base_sha}")
        tree_sha = str(base_commit["tree"]["sha"])
        entries: list[dict[str, Any]] = []
        for change in changes:
            if change.operation == "delete":
                entries.append({"path": change.path, "mode": "100644", "type": "blob", "sha": None})
                continue
            blob = await self._request(
                "POST",
                f"{prefix}/blobs",
                json={
                    "content": base64.b64encode(change.content or b"").decode(),
                    "encoding": "base64",
                },
            )
            entries.append({"path": change.path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        tree = await self._request(
            "POST", f"{prefix}/trees", json={"base_tree": tree_sha, "tree": entries}
        )
        commit = await self._request(
            "POST",
            f"{prefix}/commits",
            json={
                "message": "chore: apply approved AegisFlow change",
                "tree": tree["sha"],
                "parents": [expected_base_sha],
                "author": author,
            },
        )
        await self._request(
            "POST",
            f"{prefix}/refs",
            json={"ref": f"refs/heads/{branch_name}", "sha": commit["sha"]},
        )
        return CreatedCommit(sha=str(commit["sha"]))

    async def open_draft_pull_request(
        self,
        *,
        target: RepositoryTarget,
        branch_name: str,
        base_ref: str,
        title: str,
        body: str,
    ) -> PullRequestSnapshot:
        payload = await self._request(
            "POST",
            f"/repos/{target.owner}/{target.repository}/pulls",
            json={"title": title, "body": body, "head": branch_name, "base": base_ref, "draft": True},
        )
        return PullRequestSnapshot(
            number=payload["number"],
            title=payload["title"],
            body=payload.get("body") or "",
            state=payload["state"],
            head_ref=payload["head"]["ref"],
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        token = await self._token_provider.get_token()
        try:
            response = await self._client.request(
                method,
                self._base + path,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {token.token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=self._timeout,
                **kwargs,
            )
        except httpx.TimeoutException:
            raise GitHubTimeoutError("GitHub write request timed out") from None
        except httpx.HTTPError:
            raise GitHubUpstreamError("GitHub write request failed") from None
        if response.status_code == 404:
            raise GitHubResourceNotFoundError("GitHub resource was not found")
        if response.status_code in (401, 403):
            raise GitHubPermissionDeniedError("GitHub write permission was denied")
        if response.status_code == 429:
            raise GitHubRateLimitedError(60.0)
        if response.status_code >= 400:
            raise GitHubUpstreamError("GitHub write request failed")
        payload = response.json()
        if not isinstance(payload, dict):
            raise GitHubUpstreamError("GitHub write response was malformed")
        return payload

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
