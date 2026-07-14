from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WaterWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount_ml: Annotated[int, Field(ge=1, le=5000)]
    occurred_at: datetime | None = None
    source: Literal["quick_add", "custom"] = "custom"
    note: Annotated[str, Field(max_length=500)] | None = None

    @model_validator(mode="after")
    def require_aware_datetime(self) -> WaterWrite:
        if self.occurred_at is not None and self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must include a timezone offset")
        return self
