"""Executable state/retry ownership contract from ADR-0002."""

from __future__ import annotations

from enum import StrEnum


class RuntimeOwner(StrEnum):
    TEMPORAL = "temporal"
    LANGGRAPH = "langgraph"
    POSTGRESQL = "postgresql"
    IDEMPOTENCY_LEDGER = "idempotency_ledger"
    REDIS = "redis"


STATE_OWNERS: dict[str, RuntimeOwner] = {
    "workflow_lifecycle": RuntimeOwner.TEMPORAL,
    "human_wait": RuntimeOwner.TEMPORAL,
    "activity_retry": RuntimeOwner.TEMPORAL,
    "agent_graph_state": RuntimeOwner.LANGGRAPH,
    "tenant_run_step_approval_audit": RuntimeOwner.POSTGRESQL,
    "external_effect_claim": RuntimeOwner.IDEMPOTENCY_LEDGER,
    "realtime_notification": RuntimeOwner.REDIS,
}


def owner_of(state: str) -> RuntimeOwner:
    try:
        return STATE_OWNERS[state]
    except KeyError:
        raise ValueError(f"unknown runtime state: {state}") from None
