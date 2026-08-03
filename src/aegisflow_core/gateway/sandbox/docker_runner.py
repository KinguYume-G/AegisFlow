"""HTTP client for the narrow sandbox broker; Core never owns Docker credentials."""

from time import monotonic
import httpx

from aegisflow_core.gateway.sandbox.runner import SandboxRequest, SandboxResult


class DockerSandboxRunner:
    def __init__(self, broker_url: str, *, client: httpx.Client | None = None) -> None:
        self._url = broker_url.rstrip("/")
        self._client = client or httpx.Client(timeout=620.0)

    def run(self, request: SandboxRequest) -> SandboxResult:
        started = monotonic()
        try:
            response = self._client.post(
                f"{self._url}/v1/sandboxes/run",
                json=request.model_dump(mode="json"),
                timeout=request.timeout_seconds + 10,
            )
            response.raise_for_status()
            return SandboxResult.model_validate(response.json())
        except Exception as exc:
            return SandboxResult(
                status="internal_error", exit_code=None, stdout="",
                stderr=f"sandbox broker failure: {type(exc).__name__}",
                duration_ms=(monotonic() - started) * 1000,
                workspace_output=request.workspace_source,
            )
