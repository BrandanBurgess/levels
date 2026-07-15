from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from levels_api.models import TemplateItemType


class TodayOverrideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_date: date
    action: Literal["replace", "swap", "rest"]
    effective_split_day_id: str | None = None
    swap_target_local_date: date | None = None
    schedule_effect: Literal["one_time", "continue_from_here", "swap_forward"]
    reason: Annotated[str, Field(max_length=300)] | None = None
    expected_version: Annotated[int, Field(ge=0)]

    @model_validator(mode="after")
    def valid_variant(self) -> TodayOverrideRequest:
        if self.action == "replace":
            if self.effective_split_day_id is None or self.swap_target_local_date is not None:
                raise ValueError("replace requires effective_split_day_id only")
            if self.schedule_effect not in {"one_time", "continue_from_here"}:
                raise ValueError("replace requires one_time or continue_from_here")
        elif self.action == "swap":
            if self.effective_split_day_id is None or self.swap_target_local_date is None:
                raise ValueError("swap requires an effective day and future target date")
            if self.schedule_effect != "swap_forward":
                raise ValueError("swap requires swap_forward")
        else:
            if self.effective_split_day_id is not None or self.swap_target_local_date is not None:
                raise ValueError("rest cannot select a workout")
            if self.schedule_effect != "one_time":
                raise ValueError("rest requires one_time")
        return self


class SkipTodayRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_date: date
    schedule_effect: Literal["advance", "keep"]
    reason: Annotated[str, Field(max_length=300)] | None = None
    expected_version: Annotated[int, Field(ge=0)]


class ExercisePlanItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_template_item_id: str | None = None
    exercise_id: str
    sequence: Annotated[int, Field(ge=0)]
    item_type: TemplateItemType = TemplateItemType.ACCESSORY
    planned_sets: Annotated[int, Field(ge=1, le=20)]
    rep_min: Annotated[int, Field(ge=0)] | None = None
    rep_max: Annotated[int, Field(ge=0)] | None = None
    duration_seconds: Annotated[int, Field(ge=0)] | None = None
    distance_meters: Annotated[float, Field(ge=0)] | None = None
    rounds_target: Annotated[int, Field(ge=0)] | None = None
    rest_seconds: Annotated[int, Field(ge=0)] | None = None
    target_rir: Annotated[float, Field(ge=0, le=10)] | None = None
    superset_group: Annotated[str, Field(max_length=50)] | None = None
    optional: bool = False
    notes: Annotated[str, Field(max_length=500)] | None = None

    @model_validator(mode="after")
    def validate_rep_range(self) -> ExercisePlanItemInput:
        if self.rep_min is not None and self.rep_max is not None and self.rep_max < self.rep_min:
            raise ValueError("rep_max must be greater than or equal to rep_min")
        return self


class TodayExercisePlanUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_date: date
    source_split_day_id: str | None = None
    items: Annotated[list[ExercisePlanItemInput], Field(max_length=50)]
    scope: Literal["today_only", "save_to_split"] = "today_only"
    expected_version: Annotated[int, Field(ge=0)]

    @model_validator(mode="after")
    def validate_items(self) -> TodayExercisePlanUpdate:
        sequences = [item.sequence for item in self.items]
        if len(sequences) != len(set(sequences)) or sorted(sequences) != list(
            range(len(sequences))
        ):
            raise ValueError("item sequences must be unique and contiguous from zero")
        if self.scope == "save_to_split" and self.source_split_day_id is None:
            raise ValueError("source_split_day_id is required for save_to_split")
        return self
