"""Narrow Docker broker service; the only AegisFlow process allowed Docker access."""

from io import BytesIO
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import stat
import tarfile
from time import monotonic, time

from fastapi import FastAPI

from aegisflow_core.gateway.sandbox.runner import SandboxRequest, SandboxResult

app = FastAPI(title="AegisFlow Sandbox Broker", docs_url=None, redoc_url=None)

MAX_WORKSPACE_FILES = 1_000
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_ORPHAN_SCAN = 100
_SENSITIVE_NAMES = frozenset({".env", "id_rsa", "id_ed25519", "credentials.json", "token.txt"})
_SENSITIVE_SUFFIXES = frozenset({".key", ".pem", ".p12", ".pfx"})
_CREDENTIAL_PATTERN = re.compile(
    rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)


def _sensitive_filename(name: str) -> bool:
    lowered = name.casefold()
    return lowered in _SENSITIVE_NAMES or any(lowered.endswith(suffix) for suffix in _SENSITIVE_SUFFIXES)


def _workspace(requested: Path) -> Path:
    root = Path(os.environ.get("SANDBOX_WORKSPACE_ROOT", "/workspaces")).resolve()
    path = requested.resolve()
    if root != path and root not in path.parents:
        raise ValueError("workspace is outside the broker-owned root")
    if not path.is_dir() or path.is_symlink():
        raise ValueError("workspace must be a real directory")
    return path


def _archive(path: Path) -> bytes:
    stream = BytesIO()
    count = 0
    with tarfile.open(fileobj=stream, mode="w") as bundle:
        for child in path.rglob("*"):
            mode = child.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise ValueError("workspace contains an unsupported file type")
            count += 1
            if count > MAX_WORKSPACE_FILES:
                raise ValueError("workspace file count exceeds limit")
            if _sensitive_filename(child.name):
                raise ValueError("workspace contains a sensitive filename")
            if stat.S_ISREG(mode):
                size = child.stat().st_size
                if size > MAX_FILE_BYTES:
                    raise ValueError("workspace file size exceeds limit")
                if _CREDENTIAL_PATTERN.search(child.read_bytes()):
                    raise ValueError("workspace contains credential material")
            bundle.add(child, arcname=child.relative_to(path).as_posix(), recursive=False)
            if stream.tell() > MAX_ARCHIVE_BYTES:
                raise ValueError("workspace archive exceeds limit")
    payload = stream.getvalue()
    if len(payload) > MAX_ARCHIVE_BYTES:
        raise ValueError("workspace archive exceeds limit")
    return payload


def _extract_output(data: bytes, workspace: Path) -> None:
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError("container output archive exceeds limit")
    count = 0
    total = 0
    with tarfile.open(fileobj=BytesIO(data), mode="r:*") as bundle:
        for member in bundle.getmembers():
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != "workspace":
                raise ValueError("container output has an invalid path")
            relative = Path(*path.parts[1:])
            if not relative.parts:
                continue
            if not (member.isdir() or member.isfile()):
                raise ValueError("container output has an unsupported type")
            if _sensitive_filename(relative.name):
                raise ValueError("container output contains a sensitive filename")
            count += 1
            if count > MAX_WORKSPACE_FILES:
                raise ValueError("container output file count exceeds limit")
            if member.size > MAX_FILE_BYTES:
                raise ValueError("container output file size exceeds limit")
            total += member.size
            if total > MAX_ARCHIVE_BYTES:
                raise ValueError("container output archive exceeds limit")
            destination = (workspace / relative).resolve()
            if workspace != destination and workspace not in destination.parents:
                raise ValueError("container output escapes workspace")
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            source = bundle.extractfile(member)
            if source is None:
                raise ValueError("container output archive is invalid")
            payload = source.read(MAX_FILE_BYTES + 1)
            if len(payload) != member.size:
                raise ValueError("container output archive is invalid")
            if _CREDENTIAL_PATTERN.search(payload):
                raise ValueError("container output contains credential material")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)


def _read_bounded_archive(chunks: object) -> bytes:
    stream = BytesIO()
    for chunk in chunks:  # type: ignore[union-attr]
        stream.write(chunk)
        if stream.tell() > MAX_ARCHIVE_BYTES:
            raise ValueError("container output archive exceeds limit")
    return stream.getvalue()


def _cleanup_orphans(client: object, *, now: float | None = None, limit: int = MAX_ORPHAN_SCAN) -> int:
    current = time() if now is None else now
    removed = 0
    containers = client.containers(all=True, filters={"label": "aegisflow.sandbox=owned"})  # type: ignore[attr-defined]
    for item in containers[: max(0, min(limit, MAX_ORPHAN_SCAN))]:
        identifier = item.get("Id")
        if not identifier:
            continue
        details = client.inspect_container(identifier)  # type: ignore[attr-defined]
        labels = ((details.get("Config") or {}).get("Labels") or {})
        if labels.get("aegisflow.sandbox") != "owned":
            continue
        try:
            expires_at = float(labels.get("aegisflow.sandbox.expires_at", ""))
        except ValueError:
            continue
        if expires_at <= current:
            client.remove_container(identifier, force=True)  # type: ignore[attr-defined]
            removed += 1
    return removed


def _run(request: SandboxRequest) -> SandboxResult:
    import docker

    workspace = _workspace(request.workspace_source)
    client = docker.APIClient(base_url=os.environ.get("DOCKER_HOST", "unix:///var/run/docker.sock"))
    container_id = None
    started = monotonic()
    try:
        _cleanup_orphans(client)
        command = (
            [
                "python",
                "-B",
                "-m",
                "unittest",
                "discover",
                "-s",
                request.test_profile.test_path,
                "-v",
            ]
            if request.test_profile.name == "python_unittest"
            else [
                "python",
                "-B",
                "-m",
                "pytest",
                request.test_profile.test_path,
                "-q",
                "-p",
                "no:cacheprovider",
            ]
        )
        # Pulling the already digest-validated reference avoids tag drift and
        # matches Docker CLI behavior without accepting a mutable image name.
        client.pull(request.test_profile.image)
        host = client.create_host_config(
            network_mode="none", read_only=True, cap_drop=["ALL"], security_opt=["no-new-privileges"],
            mem_limit=f"{request.memory_limit_mb}m", nano_cpus=int(request.cpu_limit * 1_000_000_000),
            pids_limit=request.pids_limit, tmpfs={"/tmp": "rw,noexec,nosuid,size=64m"},
        )
        created = client.create_container(
            image=request.test_profile.image, command=command, user="65532:65532", working_dir="/workspace",
            host_config=host, volumes=["/workspace"], labels={
                "aegisflow.sandbox": "owned",
                "aegisflow.sandbox.expires_at": str(time() + request.timeout_seconds + 60),
            },
        )
        container_id = created["Id"]
        client.put_archive(container_id, "/workspace", _archive(workspace))
        client.start(container_id)
        wait = client.wait(container_id, timeout=request.timeout_seconds)
        exit_code = int(wait["StatusCode"])
        stdout = client.logs(container_id, stdout=True, stderr=False).decode("utf-8", "replace")
        stderr = client.logs(container_id, stdout=False, stderr=True).decode("utf-8", "replace")
        archive, _ = client.get_archive(container_id, "/workspace")
        _extract_output(_read_bounded_archive(archive), workspace)
        return SandboxResult(status="completed", exit_code=exit_code, stdout=stdout, stderr=stderr,
                             duration_ms=(monotonic()-started)*1000, workspace_output=workspace)
    except Exception as exc:
        status = "timeout" if type(exc).__name__ in {"ReadTimeout", "Timeout", "TimeoutError"} else "internal_error"
        return SandboxResult(status=status, exit_code=None, stdout="",
                             stderr=f"broker execution failed: {type(exc).__name__}",
                             duration_ms=(monotonic()-started)*1000, workspace_output=request.workspace_source)
    finally:
        if container_id:
            try: client.remove_container(container_id, force=True)
            except Exception: pass


@app.post("/v1/sandboxes/run", response_model=SandboxResult)
def run_sandbox(request: SandboxRequest) -> SandboxResult:
    return _run(request)
