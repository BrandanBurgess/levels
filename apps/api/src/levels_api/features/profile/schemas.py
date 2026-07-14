from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from levels_api.models import PreferredUnits


class PatchModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProfileUpdate(PatchModel):
    display_name: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    height_cm: Annotated[int, Field(ge=100, le=250)] | None = None
    body_weight_kg: Annotated[Decimal, Field(ge=20, le=400)] | None = None
    preferred_units: PreferredUnits | None = None
    timezone: Annotated[str, Field(min_length=1, max_length=100)] | None = None


class VisibilityUpdate(PatchModel):
    show_height: bool | None = None
    show_body_weight: bool | None = None
    show_water: bool | None = None
    show_session_summaries: bool | None = None
    show_set_details: bool | None = None
    show_public_notes: bool | None = None
    show_progress_charts: bool | None = None
    show_personal_records: bool | None = None
    show_readiness: bool | None = None


class SettingsUpdate(PatchModel):
    active_split_id: str | None = None
    week_starts_on: Annotated[int, Field(ge=0, le=6)] | None = None
    default_water_goal_ml: Annotated[int, Field(ge=250, le=10000)] | None = None
    water_quick_add_ml: (
        Annotated[list[Annotated[int, Field(ge=1, le=5000)]], Field(min_length=1, max_length=6)]
        | None
    ) = None
    default_target_rir: Annotated[Decimal, Field(ge=0, le=10)] | None = None
    default_load_increment_kg: Annotated[Decimal, Field(gt=0)] | None = None
    reduced_motion_override: bool | None = None
    visibility: VisibilityUpdate | None = None
