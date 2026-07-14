from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from levels_api.models import MeasurementType, MuscleRole


class MuscleTargetWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: Annotated[str, Field(min_length=1, max_length=100)]
    display_name: Annotated[str, Field(min_length=1, max_length=100)]
    role: MuscleRole
    intensity: Annotated[Decimal, Field(ge=0, le=1)]
    svg_region_ids: list[str]


class ExerciseWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=200)]
    slug: Annotated[str, Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$", max_length=150)]
    aliases: list[Annotated[str, Field(min_length=1, max_length=200)]] = []
    variation_group: Annotated[str, Field(min_length=1, max_length=150)]
    movement_pattern: Annotated[str, Field(min_length=1, max_length=50)]
    equipment: Annotated[str, Field(min_length=1, max_length=50)]
    measurement_type: MeasurementType
    compound: bool = False
    unilateral: bool = False
    default_rep_min: Annotated[int, Field(ge=0)] | None = None
    default_rep_max: Annotated[int, Field(ge=0)] | None = None
    default_rest_seconds: Annotated[int, Field(ge=0, le=3600)] | None = None
    automatic_progression_enabled: bool = True
    muscle_targets: Annotated[list[MuscleTargetWrite], Field(min_length=1)]

    @model_validator(mode="after")
    def valid_ranges_and_targets(self) -> ExerciseWrite:
        if (
            self.default_rep_min is not None
            and self.default_rep_max is not None
            and self.default_rep_max < self.default_rep_min
        ):
            raise ValueError("default_rep_max must be at least default_rep_min")
        keys = [(target.slug, target.role) for target in self.muscle_targets]
        if len(keys) != len(set(keys)):
            raise ValueError("muscle targets must be unique by slug and role")
        return self
