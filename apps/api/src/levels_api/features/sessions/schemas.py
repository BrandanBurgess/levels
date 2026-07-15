from __future__ import annotations

from datetime import date as Date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from levels_api.models import SetType, TemplateItemType


class StartSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_schedule_version: Annotated[int, Field(ge=0)]
    split_day_id: str | None = None
    title: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    date: Date | None = None


class SessionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["in_progress", "completed", "cancelled"] | None = None
    title: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    perceived_effort: Annotated[int, Field(ge=1, le=10)] | None = None
    notes_private: Annotated[str, Field(max_length=5000)] | None = None


class AddSessionExercise(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exercise_id: str
    expected_version: Annotated[int, Field(ge=0)]
    replace_session_exercise_id: str | None = None
    substitution_reason: Annotated[str, Field(max_length=300)] | None = None
    sequence: Annotated[int, Field(ge=0)] | None = None


class SessionExerciseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: Annotated[int, Field(ge=0)]
    exercise_id: str | None = None
    planned_sets: Annotated[int, Field(ge=1, le=20)] | None = None
    item_type: TemplateItemType | None = None
    rep_min: Annotated[int, Field(ge=0)] | None = None
    rep_max: Annotated[int, Field(ge=0)] | None = None
    duration_seconds: Annotated[int, Field(ge=0)] | None = None
    distance_meters: Annotated[float, Field(ge=0)] | None = None
    rounds_target: Annotated[int, Field(ge=0)] | None = None
    rest_seconds: Annotated[int, Field(ge=0)] | None = None
    target_rir: Annotated[float, Field(ge=0, le=10)] | None = None
    optional: bool | None = None
    notes: Annotated[str, Field(max_length=500)] | None = None
    substitution_reason: Annotated[str, Field(max_length=300)] | None = None

    @model_validator(mode="after")
    def has_update(self) -> SessionExerciseUpdate:
        if self.model_fields_set == {"expected_version"}:
            raise ValueError("at least one exercise field is required")
        if self.rep_min is not None and self.rep_max is not None and self.rep_max < self.rep_min:
            raise ValueError("rep_max must be greater than or equal to rep_min")
        return self


class ReorderSessionExercises(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: Annotated[int, Field(ge=0)]
    ordered_session_exercise_ids: Annotated[list[str], Field(min_length=1)]

    @model_validator(mode="after")
    def unique_ids(self) -> ReorderSessionExercises:
        if len(self.ordered_session_exercise_ids) != len(set(self.ordered_session_exercise_ids)):
            raise ValueError("ordered_session_exercise_ids must be unique")
        return self


class SetWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_exercise_id: str
    sequence: Annotated[int, Field(ge=1)] | None = None
    set_type: SetType
    load_kg: Annotated[float, Field(ge=0)] | None = None
    reps: Annotated[int, Field(ge=0, le=100)] | None = None
    rir: Annotated[float, Field(ge=0, le=10)] | None = None
    duration_seconds: Annotated[int, Field(ge=0)] | None = None
    distance_meters: Annotated[float, Field(ge=0)] | None = None
    rounds: Annotated[int, Field(ge=0)] | None = None
    bodyweight_assistance_kg: float | None = None
    form_quality: Annotated[int, Field(ge=1, le=5)] | None = None
    pain_flag: bool = False
    notes: Annotated[str, Field(max_length=2000)] | None = None
