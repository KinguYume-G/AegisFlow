"""Executor reasoning port."""

from collections.abc import Mapping
from typing import Protocol
from aegisflow_core.packs.delivery.contracts.plan import Plan


class PatchReasoner(Protocol):
    def generate_patch(self, plan: Plan, workspace_files: Mapping[str, str]) -> Mapping[str, str]: ...
