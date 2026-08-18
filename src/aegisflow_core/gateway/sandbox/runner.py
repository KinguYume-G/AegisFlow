"""Strict schemas and a non-executing sandbox fake."""

from pathlib import Path
import re
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, model_validator

_MAX_OUTPUT = 65_536
_DIGEST_IMAGE = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")


class TestProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    name: Literal["python_pytest", "python_unittest"]
    image: str
    test_path: str = "tests"

    @model_validator(mode="after")
    def image_must_be_digest_pinned(self) -> "TestProfile":
        if not _DIGEST_IMAGE.fullmatch(self.image):
            raise ValueError("sandbox image must be pinned by sha256 digest")
        if self.test_path.startswith(('/', '\\')) or ".." in Path(self.test_path).parts:
            raise ValueError("test_path must remain relative")
        return self


class SandboxRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    workspace_source: Path
    test_profile: TestProfile
    timeout_seconds: int = Field(default=120, ge=1, le=600)
    memory_limit_mb: int = Field(default=512, ge=64, le=2048)
    cpu_limit: float = Field(default=1.0, gt=0, le=2.0)
    pids_limit: int = Field(default=128, ge=16, le=256)


class SandboxResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    status: Literal["completed", "timeout", "resource_exceeded", "internal_error"]
    exit_code: int | None
    stdout: str
    stderr: str
    duration_ms: NonNegativeFloat
    workspace_output: Path

    @model_validator(mode="before")
    @classmethod
    def bound_output(cls, values: object) -> object:
        if isinstance(values, dict):
            values = dict(values)
            for field in ("stdout", "stderr"):
                value = str(values.get(field, ""))
                if len(value) > _MAX_OUTPUT:
                    values[field] = value[:_MAX_OUTPUT] + "[TRUNCATED]"
        return values


class SandboxRunner(Protocol):
    def run(self, request: SandboxRequest) -> SandboxResult: ...


class InMemorySandboxRunner:
    """Return a preconfigured result and never execute host processes."""

    def __init__(self, result: SandboxResult) -> None:
        self._result = result
        self.requests: list[SandboxRequest] = []

    def run(self, request: SandboxRequest) -> SandboxResult:
        self.requests.append(request)
        return self._result.model_copy(update={"workspace_output": request.workspace_source})
