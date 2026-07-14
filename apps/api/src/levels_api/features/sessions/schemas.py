from __future__ import annotations

from datetime import date as Date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from levels_api.models import PublicVisibility


class StartSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    split_day_id: str | None = None
    title: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    date: Date | None = None

    @model_validator(mode="after")
    def source_or_title(self) -> StartSession:
        if self.split_day_id is None and self.title is None:
            raise ValueError("split_day_id or title is required")
        return self


class SessionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["in_progress", "completed", "cancelled"] | None = None
    title: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    public_visibility: PublicVisibility | None = None
    perceived_effort: Annotated[int, Field(ge=1, le=10)] | None = None
    notes_private: Annotated[str, Field(max_length=5000)] | None = None
    notes_public: Annotated[str, Field(max_length=5000)] | None = None
