"""Domain-neutral idempotency command and claim result contracts."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class IdempotentCommand:
    scope: Literal["webhook_delivery", "tool_call", "compensation"]
    idempotency_key: str
    arguments_hash: str
    tenant_id: UUID
    run_id: UUID | None
    step_id: UUID | None
    tool_name: str | None


@dataclass(frozen=True, slots=True)
class Execute:
    claim_token: UUID


@dataclass(frozen=True, slots=True)
class Reuse:
    result_reference: str


@dataclass(frozen=True, slots=True)
class InProgress:
    retry_after_seconds: float


@dataclass(frozen=True, slots=True)
class FinalFailure:
    reason: str


ClaimResult = Execute | Reuse | InProgress | FinalFailure
