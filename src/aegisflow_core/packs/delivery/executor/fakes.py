"""Deterministic Executor test reasoner."""

from collections.abc import Mapping
from aegisflow_core.packs.delivery.contracts.plan import Plan


class DeterministicPatchReasoner:
    def __init__(self, fixed_responses: Mapping[str, Mapping[str, str]]) -> None:
        self._responses = {key: dict(value) for key, value in fixed_responses.items()}

    def generate_patch(self, plan: Plan, workspace_files: Mapping[str, str]) -> Mapping[str, str]:
        del workspace_files
        return dict(self._responses.get(plan.summary, {}))
