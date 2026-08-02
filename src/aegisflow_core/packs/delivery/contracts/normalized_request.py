"""Version 1 normalized request schema for DeliveryPack."""

from datetime import datetime, timedelta
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


SourceType = Literal["prd", "bug", "github_issue", "feature_request"]
SourceRef = Annotated[str, StringConstraints(max_length=2_048)]
Title = Annotated[str, StringConstraints(max_length=500)]
Body = Annotated[str, StringConstraints(max_length=1_000_000)]
IdempotencyKey = Annotated[
    str,
    StringConstraints(pattern=r"^[0-9a-f]{64}$"),
]


class NormalizedRequest(BaseModel):
    """Stable, validated input shared by downstream DeliveryPack agents."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    source_type: SourceType
    source_ref: SourceRef | None
    title: Title
    body: Body
    idempotency_key: IdempotencyKey
    received_at: datetime

    @model_validator(mode="after")
    def validate_contract(self) -> "NormalizedRequest":
        if not self.title and not self.body:
            raise ValueError("title and body cannot both be empty")
        if self.received_at.tzinfo is None or self.received_at.utcoffset() != timedelta(0):
            raise ValueError("received_at must be a timezone-aware UTC datetime")
        return self
