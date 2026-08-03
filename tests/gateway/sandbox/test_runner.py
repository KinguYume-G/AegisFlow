from pathlib import Path
import httpx
import pytest
import sys
from types import SimpleNamespace

from aegisflow_core.gateway.sandbox.docker_runner import DockerSandboxRunner
from aegisflow_core.gateway.sandbox.runner import InMemorySandboxRunner, SandboxRequest, SandboxResult, TestProfile as SandboxTestProfile
from aegisflow_core.gateway.sandbox import broker

PROFILE = SandboxTestProfile(name="python_pytest", image="python@sha256:" + "a" * 64)


def test_schema_enforces_digest_and_hard_resource_caps(tmp_path: Path) -> None:
    with pytest.raises(ValueError): SandboxTestProfile(name="python_pytest", image="python:latest")
    with pytest.raises(ValueError): SandboxRequest(workspace_source=tmp_path, test_profile=PROFILE, memory_limit_mb=2049)


def test_in_memory_runner_never_executes_and_preserves_workspace(tmp_path: Path) -> None:
    result = SandboxResult(status="completed", exit_code=0, stdout="ok", stderr="", duration_ms=1, workspace_output=tmp_path)
    actual = InMemorySandboxRunner(result).run(SandboxRequest(workspace_source=tmp_path, test_profile=PROFILE))
    assert actual.workspace_output == tmp_path and tmp_path.exists()


def test_broker_client_sends_only_structured_schema(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = __import__("json").loads(request.content)
        assert set(payload) == {"schema_version", "workspace_source", "test_profile", "timeout_seconds", "memory_limit_mb", "cpu_limit", "pids_limit"}
        return httpx.Response(200, json={"schema_version":1,"status":"completed","exit_code":0,"stdout":"","stderr":"","duration_ms":1,"workspace_output":str(tmp_path)})
    runner = DockerSandboxRunner("http://broker", client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert runner.run(SandboxRequest(workspace_source=tmp_path, test_profile=PROFILE)).status == "completed"


def test_broker_client_maps_transport_failure(tmp_path: Path) -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)
    result = DockerSandboxRunner("http://broker", client=httpx.Client(transport=httpx.MockTransport(fail))).run(
        SandboxRequest(workspace_source=tmp_path, test_profile=PROFILE))
    assert result.status == "internal_error" and "ConnectError" in result.stderr


def test_broker_rejects_workspace_outside_owned_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "owned"; root.mkdir()
    outside = tmp_path / "outside"; outside.mkdir()
    monkeypatch.setenv("SANDBOX_WORKSPACE_ROOT", str(root))
    with pytest.raises(ValueError): broker._workspace(outside)


def test_broker_runs_with_fixed_security_parameters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import io, tarfile
    root = tmp_path / "owned"; workspace = root / "job"; workspace.mkdir(parents=True)
    (workspace / "input.py").write_text("x=1\n")
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        data = b"ok\n"; info = tarfile.TarInfo("workspace/output.txt"); info.size = len(data)
        archive.addfile(info, io.BytesIO(data))

    class Client:
        def __init__(self): self.host = None; self.removed = False
        def create_host_config(self, **kwargs): self.host = kwargs; return kwargs
        def create_container(self, **kwargs): self.created = kwargs; return {"Id":"owned"}
        def put_archive(self, *args): assert args[1] == "/workspace"
        def start(self, identifier): assert identifier == "owned"
        def wait(self, *args, **kwargs): return {"StatusCode":0}
        def logs(self, *args, **kwargs): return b"passed" if kwargs.get("stdout") else b""
        def get_archive(self, *args): return [output.getvalue()], {}
        def remove_container(self, *args, **kwargs): self.removed = True
    client = Client()
    monkeypatch.setenv("SANDBOX_WORKSPACE_ROOT", str(root))
    monkeypatch.setitem(sys.modules, "docker", SimpleNamespace(APIClient=lambda **kwargs: client))
    result = broker._run(SandboxRequest(workspace_source=workspace, test_profile=PROFILE))
    assert result.status == "completed" and client.removed
    assert client.host["network_mode"] == "none" and client.host["cap_drop"] == ["ALL"]
    assert (workspace / "output.txt").read_text() == "ok\n"
