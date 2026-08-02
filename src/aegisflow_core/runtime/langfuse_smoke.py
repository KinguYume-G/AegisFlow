"""Strict post-merge smoke test for the configured Langfuse environment."""

from __future__ import annotations

import os
import sys
import time
from uuid import UUID, uuid5

from langfuse import Langfuse

from aegisflow_core.runtime.tracing import make_event_id
from aegisflow_core.settings import get_settings

_SMOKE_NAMESPACE = UUID("bd745093-8211-50fe-93c8-c696b73aa729")
_QUERY_TIMEOUT_SECONDS = 60.0
_QUERY_INTERVAL_SECONDS = 2.0


def _observation_visible(client: Langfuse, trace_id: str) -> bool:
    response = client.api.observations.get_many(
        trace_id=trace_id,
        limit=100,
        fields="core,io",
    )
    return bool(response.data)


def run_smoke() -> str:
    """Authenticate, write one sentinel observation, and prove it is queryable."""
    settings = get_settings()
    assert settings.langfuse_base_url is not None
    assert settings.langfuse_public_key is not None
    assert settings.langfuse_secret_key is not None
    assert settings.langfuse_tracing_environment is not None

    client = Langfuse(
        base_url=settings.langfuse_base_url,
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        environment=settings.langfuse_tracing_environment,
    )
    if not client.auth_check():
        raise RuntimeError("LangfuseAuthenticationFailed")

    run_seed = f"{os.environ.get('GITHUB_RUN_ID', 'local')}:{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}"
    run_id = uuid5(_SMOKE_NAMESPACE, run_seed)
    aegisflow_trace_id = uuid5(_SMOKE_NAMESPACE, f"trace:{run_seed}")
    event_id = make_event_id(
        run_id=run_id,
        step_id=None,
        agent="langfuse-smoke",
        trace_id=aegisflow_trace_id,
    )
    langfuse_trace_id = client.create_trace_id(seed=str(aegisflow_trace_id))
    observation = client.start_observation(
        name="aegisflow.langfuse-smoke",
        as_type="span",
        trace_context={"trace_id": langfuse_trace_id},
        input="aegisflow smoke sentinel",
        metadata={
            "aegisflow_smoke": True,
            "event_id": str(event_id),
            "github_run_id": os.environ.get("GITHUB_RUN_ID", "local"),
            "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
        },
    )
    observation.end()
    client.flush()

    deadline = time.monotonic() + _QUERY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if _observation_visible(client, langfuse_trace_id):
            return langfuse_trace_id
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(_QUERY_INTERVAL_SECONDS, remaining))
    raise TimeoutError("LangfuseObservationNotVisible")


def main() -> int:
    """CLI entry point that reports only non-sensitive correlation evidence."""
    try:
        trace_id = run_smoke()
    except Exception as exc:
        print(f"Langfuse smoke failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(f"Langfuse smoke succeeded: trace_id={trace_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
