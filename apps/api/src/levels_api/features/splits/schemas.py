from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from levels_api.models import TemplateItemType


class SplitItemWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    exercise_id: str
    sequence: Annotated[int, Field(ge=1)]
    item_type: TemplateItemType
    sets: Annotated[int, Field(ge=1, le=20)]
    rep_min: Annotated[int, Field(ge=0)] | None = None
    rep_max: Annotated[int, Field(ge=0)] | None = None
    duration_seconds: Annotated[int, Field(ge=0)] | None = None
    distance_meters: Annotated[Decimal, Field(ge=0)] | None = None
    rounds_target: Annotated[int, Field(ge=0)] | None = None
    rest_seconds: Annotated[int, Field(ge=0, le=3600)] | None = None
    target_rir: Annotated[Decimal, Field(ge=0, le=10)] | None = None
    optional: bool = False
    alternative_exercise_ids: list[str] = []

    @model_validator(mode="after")
    def valid_item(self) -> SplitItemWrite:
        if self.rep_min is not None and self.rep_max is not None and self.rep_max < self.rep_min:
            raise ValueError("rep_max must be at least rep_min")
        if len(self.alternative_exercise_ids) != len(set(self.alternative_exercise_ids)):
            raise ValueError("alternative exercise IDs must be unique")
        if self.exercise_id in self.alternative_exercise_ids:
            raise ValueError("an exercise cannot be its own alternative")
        return self


class SplitDayWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    name: Annotated[str, Field(min_length=1, max_length=150)]
    day_type: Annotated[str, Field(min_length=1, max_length=50)]
    sequence: Annotated[int, Field(ge=1)]
    is_optional: bool
    items: list[SplitItemWrite]

    @model_validator(mode="after")
    def unique_item_sequences(self) -> SplitDayWrite:
        sequences = [item.sequence for item in self.items]
        if len(sequences) != len(set(sequences)):
            raise ValueError("item sequences must be unique within a day")
        return self


class SplitWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=150)]
    slug: Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=150)] | None = None
    description: str | None = None
    days: list[SplitDayWrite] | None = None

    @model_validator(mode="after")
    def unique_day_sequences(self) -> SplitWrite:
        if self.days is not None:
            sequences = [day.sequence for day in self.days]
            if len(sequences) != len(set(sequences)):
                raise ValueError("day sequences must be unique within a split")
        return self
