"""Version 1 measurement schema for DeliveryPack plans."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class Measurement(BaseModel):
    """A measured non-negative value or an explicit absence of evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    status: Literal["measured", "not_available"]
    value: Decimal | None = None
    unit: str | None = None

    @field_validator("value")
    @classmethod
    def value_must_be_finite_and_non_negative(
        cls, value: Decimal | None
    ) -> Decimal | None:
        if value is not None and (not value.is_finite() or value < 0):
            raise ValueError("measurement value must be finite and non-negative")
        return value

    @field_validator("unit")
    @classmethod
    def unit_must_contain_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("measurement unit must contain non-whitespace text")
        if len(normalized) > 64:
            raise ValueError("measurement unit must not exceed 64 characters")
        return normalized

    @model_validator(mode="after")
    def state_must_be_consistent(self) -> "Measurement":
        if self.status == "not_available":
            if self.value is not None or self.unit is not None:
                raise ValueError("not_available measurement cannot contain value or unit")
        elif self.value is None or self.unit is None:
            raise ValueError("measured status requires both value and unit")
        return self
