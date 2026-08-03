"""Checkpointed state contract for the in-process Gate 1A LangGraph."""

from typing import Required, TypedDict
from uuid import UUID

from aegisflow_core.packs.delivery.contracts.clarification import Clarification
from aegisflow_core.packs.delivery.contracts.context_package import ContextPackage
from aegisflow_core.packs.delivery.contracts.normalized_request import (
    NormalizedRequest,
    SourceType,
)
from aegisflow_core.packs.delivery.contracts.plan import Plan


class AgentState(TypedDict, total=False):
    """Serializable state owned by LangGraph for one Gate 1A run."""

    run_id: Required[UUID]
    trace_id: Required[UUID]
    source_type: SourceType
    source_ref: str | None
    title: str
    body: str
    request: NormalizedRequest
    clarification: Clarification | None
    context: ContextPackage | None
    plan: Plan | None
