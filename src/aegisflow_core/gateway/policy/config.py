"""Immutable policy configuration."""

from typing import Literal
from pydantic import BaseModel, ConfigDict
from aegisflow_core.packs.delivery.contracts.plan import ToolCapability


class PolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    allowed_repository: str
    enabled_tool_capabilities: frozenset[ToolCapability]
    max_allowed_risk_level: Literal["L1", "L2", "L3"]
