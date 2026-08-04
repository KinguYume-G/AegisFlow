"""Bounded, read-only GitHub REST tools for repository reconciliation."""

import base64
import binascii
from collections.abc import Callable
import math
from typing import Any, Literal, Protocol
from urllib.parse import quote, urljoin

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from aegisflow_core.gateway.github.auth import (
    InstallationToken,
    InstallationTokenProvider,
)


_MAX_RESPONSE_BYTES = 4 * 1024 * 1024
_MAX_FILE_BYTES = 256 * 1024
_MAX_PATCH_CHARS = 65_536


class TreeEntry(BaseModel):
    """One bounded repository-tree entry."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    path: str = Field(min_length=1)
    type: Literal["file", "dir"]
    size: int | None = Field(default=None, ge=0)


class RepositoryTree(BaseModel):
    """Repository entries with an explicit truncation signal."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    entries: list[TreeEntry]
    truncated: bool


class FileContent(BaseModel):
    """Bounded UTF-8 file content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    path: str = Field(min_length=1)
    content: str
    encoding: Literal["utf-8"] = "utf-8"
    size: int = Field(ge=0)
    truncated: bool


class IssueSnapshot(BaseModel):
    """Stable subset of a GitHub Issue response."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    number: int = Field(gt=0)
    title: str
    body: str
    state: Literal["open", "closed"]
    labels: list[str]


class DiffFile(BaseModel):
    """One bounded file patch from a pull request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    path: str = Field(min_length=1)
    patch: str
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)


class PullRequestDiff(BaseModel):
    """Bounded pull-request files and patches."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    number: int = Field(gt=0)
    files: list[DiffFile]
    truncated: bool


class PullRequestSnapshot(BaseModel):
    """Read-only reconciliation view for an existing pull request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    number: int = Field(gt=0)
    title: str
    body: str
    state: Literal["open", "closed"]
    head_ref: str = Field(min_length=1)


class ActionsJob(BaseModel):
    """Bounded metadata for one Actions job; logs and steps are excluded."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=256)
    status: str = Field(min_length=1, max_length=32)
    conclusion: str | None = Field(default=None, max_length=32)
    html_url: str = Field(min_length=1, max_length=2048)


class ActionsArtifact(BaseModel):
    """Bounded metadata for one Actions artifact; content is never downloaded."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=256)
    size_in_bytes: int = Field(ge=0)
    expired: bool


class ActionsRunSnapshot(BaseModel):
    """Stable read-only view of one Actions run and bounded child metadata."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=256)
    status: str = Field(min_length=1, max_length=32)
    conclusion: str | None = Field(default=None, max_length=32)
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    html_url: str = Field(min_length=1, max_length=2048)
    jobs: list[ActionsJob]
    artifacts: list[ActionsArtifact]
    truncated: bool


class GitHubReadToolError(RuntimeError):
    """Safe base error exposed by GitHub read tools."""


class GitHubResourceNotFoundError(GitHubReadToolError):
    """The requested resource is not visible or does not exist."""


class GitHubPermissionDeniedError(GitHubReadToolError):
    """The installation is not authorized for the request."""


class GitHubRateLimitedError(GitHubReadToolError):
    """The request may be retried after the bounded delay."""

    def __init__(self, retry_after: float) -> None:
        super().__init__("GitHub read request was rate limited")
        self.retry_after = retry_after


class GitHubUpstreamError(GitHubReadToolError):
    """GitHub or the network failed without exposing raw details."""


class GitHubTimeoutError(GitHubReadToolError):
    """The configured request timeout elapsed."""


class GitHubMalformedResponseError(GitHubReadToolError):
    """GitHub returned a response outside the frozen schema."""


class _TokenProvider(Protocol):
    async def get_token(self) -> InstallationToken: ...


class _HttpClient(Protocol):
    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response: ...


class GitHubReadClient:
    """Minimal async GitHub client exposing only approved GET operations."""

    def __init__(
        self,
        *,
        token_provider: InstallationTokenProvider | _TokenProvider,
        timeout_seconds: float = 10.0,
        http_client: _HttpClient | None = None,
        api_base_url: str = "https://api.github.com",
        epoch_seconds: Callable[[], float] | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not math.isfinite(timeout_seconds):
            raise ValueError("timeout_seconds must be finite")
        self._token_provider = token_provider
        self._timeout_seconds = timeout_seconds
        self._owns_http_client = http_client is None
        self._http_client: _HttpClient = http_client or httpx.AsyncClient(
            timeout=timeout_seconds
        )
        self._api_base_url = api_base_url.rstrip("/") + "/"
        if epoch_seconds is None:
            import time

            epoch_seconds = time.time
        self._epoch_seconds = epoch_seconds

    async def read_repository_tree(
        self,
        owner: str,
        repo: str,
        ref: str,
        path: str | None = None,
        max_items: int = 200,
    ) -> RepositoryTree:
        """Read a recursive Git tree while preserving all truncation signals."""
        _require_positive("max_items", max_items)
        url = self._url(
            "repos",
            owner,
            repo,
            "git",
            "trees",
            ref,
        )
        entries: list[TreeEntry] = []
        truncated = False
        prefix = path.strip("/") if path else None
        params: dict[str, Any] | None = {"recursive": "1", "per_page": 100}

        while url:
            payload, response = await self._request_json(url, params=params)
            params = None
            if not isinstance(payload, dict) or not isinstance(payload.get("tree"), list):
                raise GitHubMalformedResponseError(
                    "GitHub repository tree response was malformed"
                )
            page = payload["tree"]
            truncated = truncated or payload.get("truncated") is True
            page_overflow = False
            for raw in page:
                entry = _parse_tree_entry(raw)
                if prefix is not None and not (
                    entry.path == prefix or entry.path.startswith(prefix + "/")
                ):
                    continue
                if len(entries) == max_items:
                    page_overflow = True
                    break
                entries.append(entry)
            next_url = self._next_link(response)
            if page_overflow or (len(entries) == max_items and next_url is not None):
                truncated = True
                break
            url = next_url

        return RepositoryTree(entries=entries, truncated=truncated)

    async def read_file_content(
        self,
        owner: str,
        repo: str,
        ref: str,
        path: str,
    ) -> FileContent:
        """Read one file without accessing the local filesystem."""
        payload, _ = await self._request_json(
            self._url("repos", owner, repo, "contents", path, preserve_slashes=True),
            params={"ref": ref},
        )
        if not isinstance(payload, dict):
            raise GitHubMalformedResponseError("GitHub file response was malformed")
        try:
            returned_path = str(payload["path"])
            size = int(payload["size"])
            encoding = payload["encoding"]
            encoded_content = payload["content"]
        except (KeyError, TypeError, ValueError):
            raise GitHubMalformedResponseError(
                "GitHub file response was malformed"
            ) from None
        if size < 0 or not isinstance(encoded_content, str):
            raise GitHubMalformedResponseError("GitHub file response was malformed")
        if size > _MAX_FILE_BYTES and encoding == "none" and not encoded_content:
            return FileContent(
                path=returned_path,
                content="",
                size=size,
                truncated=True,
            )
        if encoding != "base64":
            raise GitHubMalformedResponseError("GitHub file response was malformed")
        try:
            raw = base64.b64decode(
                "".join(encoded_content.split()),
                validate=True,
            )
        except (binascii.Error, ValueError):
            raise GitHubMalformedResponseError(
                "GitHub file content encoding was malformed"
            ) from None
        try:
            decoded = raw.decode("utf-8")
        except UnicodeDecodeError:
            return FileContent(
                path=returned_path,
                content="",
                size=size,
                truncated=True,
            )
        truncated = len(raw) < size or len(raw) > _MAX_FILE_BYTES
        if len(raw) > _MAX_FILE_BYTES:
            decoded = raw[:_MAX_FILE_BYTES].decode("utf-8", errors="ignore")
        return FileContent(
            path=returned_path,
            content=decoded,
            size=size,
            truncated=truncated,
        )

    async def read_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
    ) -> IssueSnapshot:
        """Read one issue through a stable schema."""
        _require_positive("issue_number", issue_number)
        payload, _ = await self._request_json(
            self._url("repos", owner, repo, "issues", str(issue_number))
        )
        return _parse_issue(payload)

    async def read_actions_run(
        self, owner: str, repo: str, run_id: int, max_items: int = 100
    ) -> ActionsRunSnapshot:
        """Read run/job/artifact metadata without logs, downloads, or mutations."""
        _require_positive("run_id", run_id); _require_positive("max_items", max_items)
        run, _ = await self._request_json(self._url("repos", owner, repo, "actions", "runs", str(run_id)))
        if not isinstance(run, dict):
            raise GitHubMalformedResponseError("GitHub Actions run response was malformed")
        jobs, jobs_truncated = await self._read_actions_collection(
            self._url("repos", owner, repo, "actions", "runs", str(run_id), "jobs"), "jobs", max_items
        )
        artifacts, artifacts_truncated = await self._read_actions_collection(
            self._url("repos", owner, repo, "actions", "runs", str(run_id), "artifacts"), "artifacts", max_items
        )
        try:
            return ActionsRunSnapshot(
                id=run["id"], name=run["name"], status=run["status"],
                conclusion=run.get("conclusion"), head_sha=run["head_sha"], html_url=run["html_url"],
                jobs=[_parse_actions_job(item) for item in jobs],
                artifacts=[_parse_actions_artifact(item) for item in artifacts],
                truncated=jobs_truncated or artifacts_truncated,
            )
        except (KeyError, TypeError, ValidationError):
            raise GitHubMalformedResponseError("GitHub Actions run response was malformed") from None

    async def _read_actions_collection(
        self, url: str, key: str, max_items: int
    ) -> tuple[list[Any], bool]:
        values: list[Any] = []; params: dict[str, Any] | None = {"per_page": min(100, max_items)}
        while url:
            payload, response = await self._request_json(url, params=params); params = None
            if not isinstance(payload, dict) or not isinstance(payload.get(key), list):
                raise GitHubMalformedResponseError("GitHub Actions collection response was malformed")
            for item in payload[key]:
                if len(values) == max_items:
                    return values, True
                values.append(item)
            url = self._next_link(response)
        return values, False

    async def read_pull_request_diff(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        max_items: int = 200,
    ) -> PullRequestDiff:
        """Read bounded pull-request file patches with pagination."""
        _require_positive("pr_number", pr_number)
        _require_positive("max_items", max_items)
        url = self._url("repos", owner, repo, "pulls", str(pr_number), "files")
        params: dict[str, Any] | None = {"per_page": min(100, max_items)}
        files: list[DiffFile] = []
        truncated = False
        while url:
            payload, response = await self._request_json(url, params=params)
            params = None
            if not isinstance(payload, list):
                raise GitHubMalformedResponseError(
                    "GitHub pull request files response was malformed"
                )
            page_overflow = False
            for raw in payload:
                if len(files) == max_items:
                    page_overflow = True
                    break
                diff_file, patch_truncated = _parse_diff_file(raw)
                files.append(diff_file)
                truncated = truncated or patch_truncated
            next_url = self._next_link(response)
            if page_overflow or (len(files) == max_items and next_url is not None):
                truncated = True
                break
            url = next_url
        return PullRequestDiff(
            number=pr_number,
            files=files,
            truncated=truncated,
        )

    async def find_pull_request_by_head_or_marker(
        self,
        owner: str,
        repo: str,
        head_ref: str,
        marker: str,
        max_items: int = 200,
    ) -> PullRequestSnapshot | None:
        """Find one existing PR for AF-208 reconciliation without writing."""
        _require_positive("max_items", max_items)
        if not head_ref or not marker:
            raise ValueError("head_ref and marker must be non-empty")
        url = self._url("repos", owner, repo, "pulls")
        params: dict[str, Any] | None = {
            "state": "all",
            "per_page": min(100, max_items),
        }
        inspected = 0
        matches: dict[int, PullRequestSnapshot] = {}
        while url and inspected < max_items:
            payload, response = await self._request_json(url, params=params)
            params = None
            if not isinstance(payload, list):
                raise GitHubMalformedResponseError(
                    "GitHub pull request list response was malformed"
                )
            for raw in payload:
                if inspected == max_items:
                    break
                snapshot = _parse_pull_request(raw)
                inspected += 1
                if snapshot.head_ref == head_ref or marker in (
                    snapshot.title + "\n" + snapshot.body
                ):
                    matches[snapshot.number] = snapshot
            url = self._next_link(response)
        if inspected == max_items and url is not None:
            raise GitHubReadToolError("pull request reconciliation search was truncated")
        if len(matches) > 1:
            raise GitHubReadToolError("multiple pull requests matched reconciliation")
        return next(iter(matches.values()), None)

    async def _request_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> tuple[Any, httpx.Response]:
        if not url.startswith(self._api_base_url):
            raise GitHubMalformedResponseError("GitHub pagination URL was malformed")
        token = await self._token_provider.get_token()
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        try:
            response = await self._http_client.request(
                "GET",
                url,
                params=params,
                headers=headers,
                timeout=self._timeout_seconds,
            )
        except httpx.TimeoutException:
            raise GitHubTimeoutError("GitHub read request timed out") from None
        except httpx.HTTPError:
            raise GitHubUpstreamError("GitHub read request failed") from None

        self._raise_for_status(response)
        if len(response.content) > _MAX_RESPONSE_BYTES:
            raise GitHubMalformedResponseError("GitHub response exceeded size limit")
        try:
            payload = response.json()
        except (ValueError, UnicodeDecodeError):
            raise GitHubMalformedResponseError(
                "GitHub response was not valid JSON"
            ) from None
        return payload, response

    async def aclose(self) -> None:
        """Close only the internally owned connection pool."""
        if self._owns_http_client and isinstance(self._http_client, httpx.AsyncClient):
            await self._http_client.aclose()

    def _raise_for_status(self, response: httpx.Response) -> None:
        status = response.status_code
        remaining = response.headers.get("X-RateLimit-Remaining")
        if status == 429 or (status == 403 and remaining == "0"):
            raise GitHubRateLimitedError(self._retry_after(response)) from None
        if status == 404:
            raise GitHubResourceNotFoundError(
                "GitHub resource was not found"
            ) from None
        if status in (401, 403):
            raise GitHubPermissionDeniedError(
                "GitHub read permission was denied"
            ) from None
        if status >= 400:
            raise GitHubUpstreamError("GitHub read request failed") from None

    def _retry_after(self, response: httpx.Response) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass
        reset = response.headers.get("X-RateLimit-Reset")
        if reset is not None:
            try:
                return max(0.0, float(reset) - self._epoch_seconds())
            except ValueError:
                pass
        return 60.0

    def _next_link(self, response: httpx.Response) -> str | None:
        header = response.headers.get("Link")
        if not header:
            return None
        for item in header.split(","):
            sections = [section.strip() for section in item.split(";")]
            if len(sections) < 2 or 'rel="next"' not in sections[1:]:
                continue
            candidate = sections[0]
            if not (candidate.startswith("<") and candidate.endswith(">")):
                raise GitHubMalformedResponseError(
                    "GitHub pagination header was malformed"
                )
            next_url = urljoin(self._api_base_url, candidate[1:-1])
            if not next_url.startswith(self._api_base_url):
                raise GitHubMalformedResponseError(
                    "GitHub pagination URL was malformed"
                )
            return next_url
        return None

    def _url(
        self,
        *parts: str,
        preserve_slashes: bool = False,
    ) -> str:
        encoded = [
            _quote_path(part) if preserve_slashes and index == len(parts) - 1 else quote(part, safe="")
            for index, part in enumerate(parts)
        ]
        return self._api_base_url + "/".join(encoded)


def _parse_tree_entry(raw: Any) -> TreeEntry:
    if not isinstance(raw, dict):
        raise GitHubMalformedResponseError("GitHub tree entry was malformed")
    type_map = {"blob": "file", "commit": "file", "tree": "dir"}
    try:
        entry_type = type_map[raw["type"]]
        return TreeEntry(path=raw["path"], type=entry_type, size=raw.get("size"))
    except (KeyError, TypeError, ValidationError):
        raise GitHubMalformedResponseError("GitHub tree entry was malformed") from None


def _parse_issue(payload: Any) -> IssueSnapshot:
    if not isinstance(payload, dict) or not isinstance(payload.get("labels"), list):
        raise GitHubMalformedResponseError("GitHub issue response was malformed")
    try:
        labels = [
            label if isinstance(label, str) else label["name"]
            for label in payload["labels"]
        ]
        return IssueSnapshot(
            number=payload["number"],
            title=payload["title"],
            body=payload.get("body") or "",
            state=payload["state"],
            labels=labels,
        )
    except (KeyError, TypeError, ValidationError):
        raise GitHubMalformedResponseError("GitHub issue response was malformed") from None


def _parse_diff_file(raw: Any) -> tuple[DiffFile, bool]:
    if not isinstance(raw, dict):
        raise GitHubMalformedResponseError("GitHub diff file was malformed")
    try:
        original_patch = raw.get("patch") or ""
        if not isinstance(original_patch, str):
            raise TypeError
        truncated = len(original_patch) > _MAX_PATCH_CHARS or "patch" not in raw
        return (
            DiffFile(
                path=raw["filename"],
                patch=original_patch[:_MAX_PATCH_CHARS],
                additions=raw["additions"],
                deletions=raw["deletions"],
            ),
            truncated,
        )
    except (KeyError, TypeError, ValidationError):
        raise GitHubMalformedResponseError("GitHub diff file was malformed") from None


def _parse_pull_request(raw: Any) -> PullRequestSnapshot:
    if not isinstance(raw, dict) or not isinstance(raw.get("head"), dict):
        raise GitHubMalformedResponseError(
            "GitHub pull request response was malformed"
        )
    try:
        return PullRequestSnapshot(
            number=raw["number"],
            title=raw["title"],
            body=raw.get("body") or "",
            state=raw["state"],
            head_ref=raw["head"]["ref"],
        )
    except (KeyError, TypeError, ValidationError):
        raise GitHubMalformedResponseError(
            "GitHub pull request response was malformed"
        ) from None


def _parse_actions_job(raw: Any) -> ActionsJob:
    if not isinstance(raw, dict):
        raise GitHubMalformedResponseError("GitHub Actions job was malformed")
    try:
        return ActionsJob(id=raw["id"], name=raw["name"], status=raw["status"],
                          conclusion=raw.get("conclusion"), html_url=raw["html_url"])
    except (KeyError, TypeError, ValidationError):
        raise GitHubMalformedResponseError("GitHub Actions job was malformed") from None


def _parse_actions_artifact(raw: Any) -> ActionsArtifact:
    if not isinstance(raw, dict):
        raise GitHubMalformedResponseError("GitHub Actions artifact was malformed")
    try:
        return ActionsArtifact(id=raw["id"], name=raw["name"], size_in_bytes=raw["size_in_bytes"], expired=raw["expired"])
    except (KeyError, TypeError, ValidationError):
        raise GitHubMalformedResponseError("GitHub Actions artifact was malformed") from None


def _quote_path(path: str) -> str:
    return "/".join(
        "%2E%2E" if segment == ".." else quote(segment, safe="")
        for segment in path.split("/")
    )


def _require_positive(name: str, value: int) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive")
