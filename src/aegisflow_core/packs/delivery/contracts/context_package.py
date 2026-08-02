"""Version 1 cited context schemas for DeliveryPack."""

from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


SnippetContent = Annotated[str, StringConstraints(min_length=1)]


class CitedSnippet(BaseModel):
    """An exact repository excerpt with a canonical source location."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    relative_path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    content: SnippetContent
    source_trust: Literal["repository_content"] = "repository_content"

    @field_validator("relative_path")
    @classmethod
    def path_must_be_canonical_and_relative(cls, value: str) -> str:
        if not value or "\\" in value:
            raise ValueError("relative_path must be a non-empty POSIX path")
        posix_path = PurePosixPath(value)
        windows_path = PureWindowsPath(value)
        if (
            posix_path.is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
            or ".." in posix_path.parts
            or str(posix_path) in {"", "."}
        ):
            raise ValueError("relative_path must remain within the repository root")
        return posix_path.as_posix()

    @model_validator(mode="after")
    def line_range_must_be_forward(self) -> "CitedSnippet":
        if self.end_line < self.start_line:
            raise ValueError("end_line must be greater than or equal to start_line")
        return self


class ContextPackage(BaseModel):
    """Repository evidence, unsupported claims, and bounded retrieval counters."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    snippets: list[CitedSnippet] = Field(max_length=5)
    unsupported_notes: list[str]
    scanned_file_count: int = Field(ge=0, le=200)
    skipped_file_count: int = Field(ge=0)
    security_skip_count: int = Field(ge=0)
