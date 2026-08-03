"""Narrow Docker broker service; the only AegisFlow process allowed Docker access."""

from io import BytesIO
import os
from pathlib import Path
import tarfile
from time import monotonic

from fastapi import FastAPI

from aegisflow_core.gateway.sandbox.runner import SandboxRequest, SandboxResult

app = FastAPI(title="AegisFlow Sandbox Broker", docs_url=None, redoc_url=None)


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
    with tarfile.open(fileobj=stream, mode="w") as bundle:
        for child in path.rglob("*"):
            if child.is_symlink():
                raise ValueError("workspace symlinks are forbidden")
            bundle.add(child, arcname=child.relative_to(path).as_posix(), recursive=False)
    return stream.getvalue()


def _run(request: SandboxRequest) -> SandboxResult:
    import docker

    workspace = _workspace(request.workspace_source)
    client = docker.APIClient(base_url=os.environ.get("DOCKER_HOST", "unix:///var/run/docker.sock"))
    container_id = None
    started = monotonic()
    try:
        command = ["python", "-m", "pytest", request.test_profile.test_path, "-q"]
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
            host_config=host, volumes=["/workspace"], labels={"aegisflow.sandbox":"owned"},
        )
        container_id = created["Id"]
        client.put_archive(container_id, "/workspace", _archive(workspace))
        client.start(container_id)
        wait = client.wait(container_id, timeout=request.timeout_seconds)
        exit_code = int(wait["StatusCode"])
        stdout = client.logs(container_id, stdout=True, stderr=False).decode("utf-8", "replace")
        stderr = client.logs(container_id, stdout=False, stderr=True).decode("utf-8", "replace")
        archive, _ = client.get_archive(container_id, "/workspace")
        output = BytesIO(b"".join(archive))
        with tarfile.open(fileobj=output) as bundle:
            for member in bundle.getmembers():
                relative = Path(member.name).relative_to("workspace")
                destination = (workspace / relative).resolve()
                if workspace != destination and workspace not in destination.parents:
                    raise ValueError("container output escapes workspace")
                if member.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    source = bundle.extractfile(member)
                    if source is None:
                        raise ValueError("container output archive is invalid")
                    destination.write_bytes(source.read())
        return SandboxResult(status="completed", exit_code=exit_code, stdout=stdout, stderr=stderr,
                             duration_ms=(monotonic()-started)*1000, workspace_output=workspace)
    except Exception as exc:
        return SandboxResult(status="internal_error", exit_code=None, stdout="",
                             stderr=f"broker execution failed: {type(exc).__name__}",
                             duration_ms=(monotonic()-started)*1000, workspace_output=request.workspace_source)
    finally:
        if container_id:
            try: client.remove_container(container_id, force=True)
            except Exception: pass


@app.post("/v1/sandboxes/run", response_model=SandboxResult)
def run_sandbox(request: SandboxRequest) -> SandboxResult:
    return _run(request)
