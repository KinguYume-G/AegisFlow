from uuid import UUID, uuid4
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from aegisflow_core.gateway.github.pull_request import (
    CreatedCommit,
    DraftPullRequestResult,
    Execute,
    FileChange,
    IdempotencyInProgressError,
    InProgress,
    MissingApprovalError,
    PullRequestSnapshot,
    Reuse,
    WriteAuthorization,
    GitHubWriteClient,
    create_draft_pull_request,
    create_draft_pull_request_candidate,
    draft_pr_action_preview,
    digest_action_preview,
    digest_file_changes,
)
from aegisflow_core.gateway.policy.gate import RepositoryTarget
from aegisflow_core.gateway.github.auth import InstallationToken
from aegisflow_core.gateway.github.read_tools import (
    GitHubPermissionDeniedError,
    GitHubResourceNotFoundError,
    GitHubTimeoutError,
    GitHubUpstreamError,
)


class Authorizer:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed

    async def verify(
        self, authorization: WriteAuthorization, digest: str, action_digest: str
    ) -> None:
        if (
            not self.allowed
            or digest != authorization.content_digest
            or action_digest != authorization.action_digest
        ):
            raise ValueError("not approved")


class Guard:
    def __init__(self, result: object) -> None:
        self.result = result
        self.completed: list[tuple[UUID, str]] = []
        self.failed: list[tuple[UUID, bool, str]] = []

    async def begin(self, command: object) -> object:
        self.command = command
        return self.result

    async def complete(self, token: UUID, reference: str) -> None:
        self.completed.append((token, reference))

    async def fail(self, token: UUID, retryable: bool, reason: str) -> None:
        self.failed.append((token, retryable, reason))


class Reader:
    def __init__(self, existing: PullRequestSnapshot | None = None) -> None:
        self.existing = existing
        self.calls = 0

    async def find_pull_request_by_head_or_marker(self, *args: object, **kwargs: object) -> PullRequestSnapshot | None:
        self.calls += 1
        return self.existing


class Writer:
    def __init__(self) -> None:
        self.commit_calls = 0
        self.pr_calls = 0

    async def create_commit_from_changes(self, **kwargs: object) -> CreatedCommit:
        self.commit_calls += 1
        assert kwargs["author"] == {
            "name": "AegisFlow Bot",
            "email": "aegisflow-bot@users.noreply.github.com",
        }
        return CreatedCommit(sha="b" * 40)

    async def open_draft_pull_request(self, **kwargs: object) -> PullRequestSnapshot:
        self.pr_calls += 1
        assert "<!-- aegisflow:marker " in str(kwargs["body"])
        return PullRequestSnapshot(
            number=7,
            title=str(kwargs["title"]),
            body=str(kwargs["body"]),
            state="open",
            head_ref=str(kwargs["branch_name"]),
        )


def authorization(
    changes: tuple[FileChange, ...], *, effect_mode: str = "github"
) -> WriteAuthorization:
    run_id = uuid4()
    target = RepositoryTarget("owner", "fixture")
    content_digest = digest_file_changes(changes)
    preview = draft_pr_action_preview(
        effect_mode=effect_mode,  # type: ignore[arg-type]
        target=target,
        base_ref="main",
        base_sha="a" * 40,
        branch_name=f"aegisflow/run-{run_id}",
        changes=changes,
        risk="L3",
    )
    return WriteAuthorization(
        approval_id=uuid4(),
        tenant_id=uuid4(),
        run_id=run_id,
        step_id=uuid4(),
        repository_target=target,
        base_ref="main",
        base_sha="a" * 40,
        content_digest=content_digest,
        action_digest=digest_action_preview(preview),
        effect_mode=effect_mode,
        risk="L3",
    )


@pytest.mark.asyncio
async def test_verified_write_creates_one_draft_pr_and_completes_claim() -> None:
    changes = (FileChange(path="src/app.py", operation="add", content=b"ok\n"),)
    auth = authorization(changes)
    claim = uuid4()
    guard, reader, writer = Guard(Execute(claim)), Reader(), Writer()

    result = await create_draft_pull_request(
        github_client=writer,
        read_client=reader,
        changes=changes,
        authorization=auth,
        approval_authorizer=Authorizer(),
        idempotency_guard=guard,
    )

    assert result.pull_request_number == 7
    assert result.branch_name == f"aegisflow/run-{auth.run_id}"
    assert result.commit_sha == "b" * 40
    assert not result.reused_existing
    assert writer.commit_calls == writer.pr_calls == 1
    assert guard.completed[0][0] == claim


@pytest.mark.asyncio
async def test_dry_run_creates_candidate_without_any_github_call() -> None:
    changes = (FileChange(path="src/app.py", operation="add", content=b"ok\n"),)
    auth = authorization(changes, effect_mode="dry_run")
    claim = uuid4()
    guard, reader, writer = Guard(Execute(claim)), Reader(), Writer()

    result = await create_draft_pull_request_candidate(
        github_client=writer,
        read_client=reader,
        changes=changes,
        authorization=auth,
        approval_authorizer=Authorizer(),
        idempotency_guard=guard,
    )

    assert result.effect_mode == "dry_run"
    assert result.pull_request_url is None
    assert result.pull_request_number is None
    assert result.candidate_reference == f"aegisflow://draft-pr-candidates/{auth.run_id}"
    assert result.branch_name == f"aegisflow/run-{auth.run_id}"
    assert reader.calls == writer.commit_calls == writer.pr_calls == 0
    assert guard.completed[0][0] == claim


def test_action_digest_binds_scope_effect_and_content() -> None:
    preview = {
        "effect": "create_draft_pr_candidate",
        "effect_mode": "dry_run",
        "repository": "owner/fixture",
        "base_ref": "main",
        "base_sha": "a" * 40,
        "branch_name": "aegisflow/run-example",
        "changed_files": ["src/app.py"],
        "content_digest": "b" * 64,
        "risk": "L3",
    }
    original = digest_action_preview(preview)

    assert original != digest_action_preview({**preview, "repository": "other/fixture"})
    assert original != digest_action_preview({**preview, "base_sha": "c" * 40})
    assert original != digest_action_preview({**preview, "effect_mode": "github"})
    assert original != digest_action_preview({**preview, "content_digest": "d" * 64})

@pytest.mark.asyncio
async def test_dry_run_reuse_remains_a_candidate_and_never_calls_github() -> None:
    changes = (FileChange(path="a.txt", operation="add", content=b"a"),)
    auth = authorization(changes, effect_mode="dry_run")
    prior = DraftPullRequestResult(
        effect_mode="dry_run",
        pull_request_url=None,
        pull_request_number=None,
        candidate_reference=f"aegisflow://draft-pr-candidates/{auth.run_id}",
        branch_name=f"aegisflow/run-{auth.run_id}",
        reused_existing=False,
    )
    writer, reader = Writer(), Reader()

    result = await create_draft_pull_request_candidate(
        github_client=writer,
        read_client=reader,
        changes=changes,
        authorization=auth,
        approval_authorizer=Authorizer(),
        idempotency_guard=Guard(Reuse(prior.model_dump_json())),
    )

    assert result.effect_mode == "dry_run" and result.reused_existing
    assert result.pull_request_url is None
    assert reader.calls == writer.commit_calls == writer.pr_calls == 0


@pytest.mark.asyncio
async def test_missing_approval_fails_before_claim_or_github() -> None:
    changes = (FileChange(path="a.txt", operation="add", content=b"a"),)
    writer = Writer()
    with pytest.raises(MissingApprovalError):
        await create_draft_pull_request(
            github_client=writer,
            read_client=Reader(),
            changes=changes,
            authorization=authorization(changes),
            approval_authorizer=Authorizer(False),
            idempotency_guard=Guard(Execute(uuid4())),
        )
    assert writer.commit_calls == writer.pr_calls == 0


@pytest.mark.asyncio
async def test_reuse_short_circuits_all_remote_calls() -> None:
    changes = (FileChange(path="a.txt", operation="add", content=b"a"),)
    prior = DraftPullRequestResult(
        pull_request_url="https://github.com/owner/fixture/pull/3",
        pull_request_number=3,
        branch_name="aegisflow/run-prior",
        reused_existing=False,
    )
    writer, reader = Writer(), Reader()
    result = await create_draft_pull_request(
        github_client=writer,
        read_client=reader,
        changes=changes,
        authorization=authorization(changes),
        approval_authorizer=Authorizer(),
        idempotency_guard=Guard(Reuse(prior.model_dump_json())),
    )
    assert result.reused_existing
    assert reader.calls == writer.commit_calls == writer.pr_calls == 0


@pytest.mark.asyncio
async def test_in_progress_never_calls_remote() -> None:
    changes = (FileChange(path="a.txt", operation="add", content=b"a"),)
    writer = Writer()
    with pytest.raises(IdempotencyInProgressError):
        await create_draft_pull_request(
            github_client=writer,
            read_client=Reader(),
            changes=changes,
            authorization=authorization(changes),
            approval_authorizer=Authorizer(),
            idempotency_guard=Guard(InProgress(2.0)),
        )
    assert writer.commit_calls == writer.pr_calls == 0


@pytest.mark.asyncio
async def test_remote_marker_reconciliation_reuses_without_write() -> None:
    changes = (FileChange(path="a.txt", operation="add", content=b"a"),)
    existing = PullRequestSnapshot(
        number=9, title="existing", body="marker", state="open", head_ref="branch"
    )
    writer = Writer()
    result = await create_draft_pull_request(
        github_client=writer,
        read_client=Reader(existing),
        changes=changes,
        authorization=authorization(changes),
        approval_authorizer=Authorizer(),
        idempotency_guard=Guard(Execute(uuid4())),
    )
    assert result.reused_existing and result.pull_request_number == 9
    assert writer.commit_calls == writer.pr_calls == 0


@pytest.mark.asyncio
async def test_empty_or_duplicate_changes_are_rejected_before_claim() -> None:
    change = FileChange(path="a.txt", operation="add", content=b"a")
    auth = authorization((change,))
    for changes in ((), (change, change)):
        with pytest.raises(ValueError):
            await create_draft_pull_request(
                github_client=Writer(), read_client=Reader(), changes=changes,
                authorization=auth, approval_authorizer=Authorizer(),
                idempotency_guard=Guard(Execute(uuid4())),
            )


def test_file_changes_reject_traversal_and_invalid_delete_content() -> None:
    with pytest.raises(ValueError):
        FileChange(path="../secret", operation="add", content=b"x")
    with pytest.raises(ValueError):
        FileChange(path="a", operation="delete", content=b"x")


class TokenProvider:
    async def get_token(self) -> InstallationToken:
        return InstallationToken(
            token="test-token",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )


@pytest.mark.asyncio
async def test_write_client_runs_git_data_sequence_and_opens_draft() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        path = request.url.path
        if path.endswith("/git/ref/heads/aegisflow/run-x"):
            return httpx.Response(404, request=request)
        if path.endswith("/git/commits/" + "a" * 40):
            payload = {"tree": {"sha": "t" * 40}}
        elif path.endswith("/git/blobs"):
            payload = {"sha": "c" * 40}
        elif path.endswith("/git/trees"):
            payload = {"sha": "d" * 40}
        elif path.endswith("/git/commits"):
            payload = {"sha": "e" * 40}
        elif path.endswith("/git/refs"):
            payload = {"ref": "refs/heads/aegisflow/run-x"}
        elif path.endswith("/pulls"):
            payload = {
                "number": 8, "title": "draft", "body": "marker", "state": "open",
                "head": {"ref": "aegisflow/run-x"},
            }
        else:
            return httpx.Response(500, request=request)
        return httpx.Response(201, json=payload, request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    writer = GitHubWriteClient(token_provider=TokenProvider(), http_client=client)
    commit = await writer.create_commit_from_changes(
        target=RepositoryTarget("owner", "repo"), expected_base_sha="a" * 40,
        branch_name="aegisflow/run-x",
        changes=(
            FileChange(path="new.txt", operation="add", content=b"new"),
            FileChange(path="old.txt", operation="delete"),
        ),
        author={"name": "Bot", "email": "bot@example.invalid"},
    )
    pr = await writer.open_draft_pull_request(
        target=RepositoryTarget("owner", "repo"), branch_name="aegisflow/run-x",
        base_ref="main", title="draft", body="marker",
    )
    assert commit.sha == "e" * 40 and pr.number == 8
    assert paths == [
        "/repos/owner/repo/git/ref/heads/aegisflow/run-x",
        "/repos/owner/repo/git/commits/" + "a" * 40,
        "/repos/owner/repo/git/blobs",
        "/repos/owner/repo/git/trees",
        "/repos/owner/repo/git/commits",
        "/repos/owner/repo/git/refs",
        "/repos/owner/repo/pulls",
    ]
    await writer.aclose()
    await client.aclose()


@pytest.mark.asyncio
async def test_write_client_reuses_partial_side_effect_branch() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"object": {"sha": "f" * 40}}, request=request
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    writer = GitHubWriteClient(token_provider=TokenProvider(), http_client=client)
    commit = await writer.create_commit_from_changes(
        target=RepositoryTarget("owner", "repo"), expected_base_sha="a" * 40,
        branch_name="aegisflow/run-existing",
        changes=(FileChange(path="a", operation="add", content=b"a"),),
        author={"name": "Bot", "email": "bot@example.invalid"},
    )
    assert commit.sha == "f" * 40
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "error"),
    [
        (404, GitHubResourceNotFoundError),
        (403, GitHubPermissionDeniedError),
        (500, GitHubUpstreamError),
    ],
)
async def test_write_client_maps_safe_http_errors(status: int, error: type[Exception]) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(status, request=request))
    client = httpx.AsyncClient(transport=transport)
    writer = GitHubWriteClient(token_provider=TokenProvider(), http_client=client)
    with pytest.raises(error):
        await writer.create_commit_from_changes(
            target=RepositoryTarget("owner", "repo"), expected_base_sha="a" * 40,
            branch_name="branch", changes=(FileChange(path="a", operation="add", content=b"a"),),
            author={"name": "Bot", "email": "bot@example.invalid"},
        )
    await client.aclose()


class TimeoutTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)


@pytest.mark.asyncio
async def test_write_client_maps_timeout() -> None:
    client = httpx.AsyncClient(transport=TimeoutTransport())
    writer = GitHubWriteClient(token_provider=TokenProvider(), http_client=client)
    with pytest.raises(GitHubTimeoutError):
        await writer.create_commit_from_changes(
            target=RepositoryTarget("owner", "repo"), expected_base_sha="a" * 40,
            branch_name="branch", changes=(FileChange(path="a", operation="add", content=b"a"),),
            author={"name": "Bot", "email": "bot@example.invalid"},
        )
    await client.aclose()
