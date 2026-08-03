"""Deterministic policy decision contract."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, model_validator


class PolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    decision: Literal["allow", "deny"]
    violated_rule: Literal[
        "repository_scope",
        "tool_capability_scope",
        "risk_ceiling",
        "prompt_injection",
        "prompt_injection_unknown",
    ] | None = None
    reasons: list[str]

    @model_validator(mode="after")
    def consistent(self) -> "PolicyDecision":
        if self.decision == "allow" and (self.violated_rule is not None or self.reasons):
            raise ValueError("allow cannot contain violations")
        if self.decision == "deny" and (self.violated_rule is None or not self.reasons):
            raise ValueError("deny requires a violated rule and reasons")
        return self
