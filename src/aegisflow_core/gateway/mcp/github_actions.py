"""MCP adapter for the sole approved GitHub Actions read-only scenario."""

from hashlib import sha256
import json
from typing import Callable
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from aegisflow_core.gateway.github.read_tools import ActionsRunSnapshot, GitHubReadClient


class GitHubActionsReadInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    owner: str = Field(pattern=r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
    repository: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,100}$")
    run_id: int = Field(gt=0)
    max_items: int = Field(default=100, ge=1, le=100)


def _schema_hash(model: type[BaseModel]) -> str:
    encoded = json.dumps(model.model_json_schema(), sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


class GitHubActionsReadAdapter:
    identifier = "internal.github.actions.read"
    input_schema_hash = _schema_hash(GitHubActionsReadInput)
    output_schema_hash = _schema_hash(ActionsRunSnapshot)

    def __init__(self, client_factory: Callable[[object], GitHubReadClient] | None = None) -> None:
        self._client_factory = client_factory or (lambda credentials: GitHubReadClient(token_provider=credentials))  # type: ignore[arg-type]

    def validate_input(self, arguments: dict[str, object]) -> bool:
        try: GitHubActionsReadInput.model_validate(arguments)
        except ValidationError: return False
        return True

    def validate_output(self, result: object) -> bool:
        try: ActionsRunSnapshot.model_validate(result)
        except ValidationError: return False
        return True

    async def invoke(self, arguments: dict[str, object], credentials: object | None) -> object:
        if credentials is None:
            raise RuntimeError("GitHub Actions read credentials unavailable")
        value = GitHubActionsReadInput.model_validate(arguments)
        client = self._client_factory(credentials)
        snapshot = await client.read_actions_run(value.owner, value.repository, value.run_id, value.max_items)
        return snapshot.model_dump(mode="json")
