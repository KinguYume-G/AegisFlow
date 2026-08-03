"""Contract, pagination, and failure tests for AF-202 GitHub read tools."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest

from aegisflow_core.gateway.github.auth import InstallationToken
from aegisflow_core.gateway.github.read_tools import (
    GitHubMalformedResponseError,
    GitHubPermissionDeniedError,
    GitHubRateLimitedError,
    GitHubReadClient,
    GitHubReadToolError,
    GitHubResourceNotFoundError,
    GitHubTimeoutError,
    GitHubUpstreamError,
)


class FakeTokenProvider:
    def __init__(self, token: str = "sensitive-installation-token") -> None:
        self.token = token
        self.calls = 0

    async def get_token(self) -> InstallationToken:
        self.calls += 1
        return InstallationToken(
            token=self.token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )


def _client(
    handler: httpx.MockTransport,
    *,
    provider: FakeTokenProvider | None = None,
    epoch_seconds: float = 1_000.0,
) -> tuple[GitHubReadClient, FakeTokenProvider, httpx.AsyncClient]:
    resolved_provider = provider or FakeTokenProvider()
    http_client = httpx.AsyncClient(transport=handler)
    return (
        GitHubReadClient(
            token_provider=resolved_provider,
            http_client=http_client,
            api_base_url="https://api.github.test",
            timeout_seconds=2.5,
            epoch_seconds=lambda: epoch_seconds,
        ),
        resolved_provider,
        http_client,
    )


@pytest.mark.anyio
async def test_read_repository_tree_paginates_and_preserves_truncation() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(
                200,
                json={
                    "tree": [
                        {"path": "src", "type": "tree", "size": None},
                        {"path": "src/app.py", "type": "blob", "size": 10},
                    ],
                    "truncated": False,
                },
                headers={
                    "Link": '<https://api.github.test/repos/o/r/git/trees/main?page=2>; rel="next"'
                },
            )
        return httpx.Response(
            200,
            json={
                "tree": [{"path": "README.md", "type": "blob", "size": 20}],
                "truncated": True,
            },
        )

    client, provider, http_client = _client(httpx.MockTransport(handler))
    try:
        result = await client.read_repository_tree("o", "r", "main")
    finally:
        await http_client.aclose()

    assert [(entry.path, entry.type) for entry in result.entries] == [
        ("src", "dir"),
        ("src/app.py", "file"),
        ("README.md", "file"),
    ]
    assert result.truncated is True
    assert len(requests) == 2
    assert provider.calls == 2
    assert all(request.method == "GET" for request in requests)


@pytest.mark.anyio
async def test_read_repository_tree_respects_max_items_without_next_request() -> None:
    requests = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(
            200,
            json={
                "tree": [
                    {"path": "a", "type": "blob", "size": 1},
                    {"path": "b", "type": "blob", "size": 1},
                    {"path": "c", "type": "blob", "size": 1},
                ],
                "truncated": False,
            },
            headers={
                "Link": '<https://api.github.test/repos/o/r/git/trees/main?page=2>; rel="next"'
            },
        )

    client, _, http_client = _client(httpx.MockTransport(handler))
    try:
        result = await client.read_repository_tree("o", "r", "main", max_items=2)
    finally:
        await http_client.aclose()

    assert [entry.path for entry in result.entries] == ["a", "b"]
    assert result.truncated is True
    assert requests == 1


@pytest.mark.anyio
async def test_exact_item_limit_without_next_page_is_not_truncated() -> None:
    client, _, http_client = _client(
        httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                json={
                    "tree": [
                        {"path": "a", "type": "blob", "size": 1},
                        {"path": "b", "type": "blob", "size": 1},
                    ],
                    "truncated": False,
                },
            )
        )
    )
    try:
        result = await client.read_repository_tree("o", "r", "main", max_items=2)
    finally:
        await http_client.aclose()

    assert result.truncated is False


@pytest.mark.anyio
async def test_read_file_content_decodes_utf8_and_marks_binary() -> None:
    responses = iter(
        [
            httpx.Response(
                200,
                json={
                    "path": "hello.txt",
                    "encoding": "base64",
                    "content": "aGVsbG8=",
                    "size": 5,
                },
            ),
            httpx.Response(
                200,
                json={
                    "path": "large.txt",
                    "encoding": "none",
                    "content": "",
                    "size": 300_000,
                },
            ),
            httpx.Response(
                200,
                json={
                    "path": "binary.dat",
                    "encoding": "base64",
                    "content": "/wA=",
                    "size": 2,
                },
            ),
        ]
    )
    client, _, http_client = _client(
        httpx.MockTransport(lambda _request: next(responses))
    )
    try:
        text = await client.read_file_content("o", "r", "main", "hello.txt")
        binary = await client.read_file_content("o", "r", "main", "binary.dat")
        large = await client.read_file_content("o", "r", "main", "large.txt")
    finally:
        await http_client.aclose()

    assert text.content == "hello"
    assert text.truncated is False
    assert binary.content == ""
    assert binary.truncated is True
    assert large.content == ""
    assert large.truncated is True


@pytest.mark.anyio
async def test_read_issue_maps_fields_and_reuses_provider() -> None:
    provider = FakeTokenProvider()
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "number": 21,
                "title": "Read tools",
                "body": "body",
                "state": "open",
                "labels": [{"name": "type:mcp"}, {"name": "priority:P0"}],
            },
        )

    client, _, http_client = _client(httpx.MockTransport(handler), provider=provider)
    try:
        first = await client.read_issue("o", "r", 21)
        await client.read_issue("o", "r", 21)
    finally:
        await http_client.aclose()

    assert first.number == 21
    assert first.labels == ["type:mcp", "priority:P0"]
    assert provider.calls == 2
    assert all(
        request.headers["Authorization"] == "Bearer sensitive-installation-token"
        for request in requests
    )


@pytest.mark.anyio
async def test_read_pull_request_diff_aggregates_and_truncates_patch() -> None:
    patch = "+" + ("x" * 70_000)
    client, _, http_client = _client(
        httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                json=[
                    {
                        "filename": "src/app.py",
                        "patch": patch,
                        "additions": 2,
                        "deletions": 1,
                    }
                ],
            )
        )
    )
    try:
        result = await client.read_pull_request_diff("o", "r", 7)
    finally:
        await http_client.aclose()

    assert result.number == 7
    assert result.files[0].path == "src/app.py"
    assert len(result.files[0].patch) == 65_536
    assert result.truncated is True


@pytest.mark.anyio
async def test_find_pull_request_by_head_or_marker_none_unique_and_conflict() -> None:
    payloads = iter(
        [
            [],
            [
                {
                    "number": 8,
                    "title": "Draft",
                    "body": "<!-- marker-1 -->",
                    "state": "open",
                    "head": {"ref": "aegisflow/run-1"},
                }
            ],
            [
                {
                    "number": 8,
                    "title": "Draft",
                    "body": "<!-- marker-1 -->",
                    "state": "open",
                    "head": {"ref": "aegisflow/run-1"},
                },
                {
                    "number": 9,
                    "title": "Duplicate marker-1",
                    "body": "",
                    "state": "open",
                    "head": {"ref": "other"},
                },
            ],
        ]
    )
    methods: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        return httpx.Response(200, json=next(payloads))

    client, _, http_client = _client(httpx.MockTransport(handler))
    try:
        assert (
            await client.find_pull_request_by_head_or_marker(
                "o", "r", "aegisflow/run-1", "marker-1"
            )
            is None
        )
        match = await client.find_pull_request_by_head_or_marker(
            "o", "r", "aegisflow/run-1", "marker-1"
        )
        assert match is not None and match.number == 8
        with pytest.raises(GitHubReadToolError, match="multiple pull requests"):
            await client.find_pull_request_by_head_or_marker(
                "o", "r", "aegisflow/run-1", "marker-1"
            )
    finally:
        await http_client.aclose()

    assert methods == ["GET", "GET", "GET"]


@pytest.mark.parametrize(
    ("status", "headers", "expected"),
    [
        (404, {}, GitHubResourceNotFoundError),
        (401, {}, GitHubPermissionDeniedError),
        (403, {}, GitHubPermissionDeniedError),
        (500, {}, GitHubUpstreamError),
        (502, {}, GitHubUpstreamError),
    ],
)
@pytest.mark.anyio
async def test_maps_http_failures_without_raw_exception(
    status: int,
    headers: dict[str, str],
    expected: type[GitHubReadToolError],
) -> None:
    client, _, http_client = _client(
        httpx.MockTransport(
            lambda _request: httpx.Response(status, headers=headers, json={})
        )
    )
    try:
        with pytest.raises(expected) as caught:
            await client.read_issue("o", "r", 1)
    finally:
        await http_client.aclose()

    assert caught.value.__cause__ is None
    assert not isinstance(caught.value, httpx.HTTPError)


@pytest.mark.parametrize(
    ("status", "headers", "retry_after"),
    [
        (429, {"Retry-After": "15"}, 15.0),
        (
            403,
            {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1030"},
            30.0,
        ),
    ],
)
@pytest.mark.anyio
async def test_maps_rate_limit_to_retryable_error(
    status: int, headers: dict[str, str], retry_after: float
) -> None:
    client, _, http_client = _client(
        httpx.MockTransport(
            lambda _request: httpx.Response(status, headers=headers, json={})
        )
    )
    try:
        with pytest.raises(GitHubRateLimitedError) as caught:
            await client.read_issue("o", "r", 1)
    finally:
        await http_client.aclose()

    assert caught.value.retry_after == retry_after


@pytest.mark.anyio
async def test_maps_timeout_and_malformed_response() -> None:
    timeout_client, _, timeout_http = _client(
        httpx.MockTransport(
            lambda request: (_ for _ in ()).throw(
                httpx.ReadTimeout("sensitive timeout", request=request)
            )
        )
    )
    malformed_client, _, malformed_http = _client(
        httpx.MockTransport(
            lambda _request: httpx.Response(
                200, content=b"not-json", headers={"Content-Type": "text/plain"}
            )
        )
    )
    missing_client, _, missing_http = _client(
        httpx.MockTransport(lambda _request: httpx.Response(200, json={}))
    )
    try:
        with pytest.raises(GitHubTimeoutError) as timeout:
            await timeout_client.read_issue("o", "r", 1)
        with pytest.raises(GitHubMalformedResponseError):
            await malformed_client.read_issue("o", "r", 1)
        with pytest.raises(GitHubMalformedResponseError):
            await missing_client.read_issue("o", "r", 1)
    finally:
        await timeout_http.aclose()
        await malformed_http.aclose()
        await missing_http.aclose()

    assert timeout.value.__cause__ is None


@pytest.mark.anyio
async def test_rejects_invalid_limits_and_never_logs_token(
    caplog: pytest.LogCaptureFixture,
) -> None:
    token = "never-log-this-token"
    provider = FakeTokenProvider(token)
    client, _, http_client = _client(
        httpx.MockTransport(lambda _request: httpx.Response(404, json={})),
        provider=provider,
    )
    try:
        with pytest.raises(ValueError):
            await client.read_repository_tree("o", "r", "main", max_items=0)
        with pytest.raises(GitHubResourceNotFoundError):
            await client.read_file_content("o", "r", "main", "../secret")
    finally:
        await http_client.aclose()

    assert token not in caplog.text


def test_schema_rejects_extra_fields() -> None:
    from aegisflow_core.gateway.github.read_tools import RepositoryTree

    with pytest.raises(ValueError):
        RepositoryTree(entries=[], truncated=False, unexpected=True)
