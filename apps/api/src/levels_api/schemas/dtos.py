from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class StrictDto(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PublicProfileDto(StrictDto):
    display_name: str
    height_cm: int | None = None
    body_weight_kg: float | None = None
    preferred_units: str
    timezone: str
    avatar_variant: str


class AdminProfileDto(PublicProfileDto):
    id: str


class VisibilityDto(StrictDto):
    show_height: bool
    show_body_weight: bool
    show_water: bool
    show_session_summaries: bool
    show_set_details: bool
    show_public_notes: bool
    show_progress_charts: bool
    show_personal_records: bool
    show_readiness: bool


class SettingsDto(StrictDto):
    active_split_id: str | None
    default_water_goal_ml: int
    water_quick_add_ml: list[int]
    default_target_rir: float
    default_load_increment_kg: float
    visibility: VisibilityDto


class PublicSetDto(StrictDto):
    id: str
    sequence: int
    set_type: str
    load_kg: float | None
    reps: int | None
    rir: float | None
    duration_seconds: int | None
    distance_meters: float | None
    rounds: int | None
    form_quality: int | None
    pain_flag: bool
    completed_at: datetime


class AdminSetDto(PublicSetDto):
    notes: str | None


class PublicSessionExerciseDto(StrictDto):
    id: str
    exercise_id: str
    display_name: str
    variation_group: str
    sequence: int
    rep_min: int | None
    rep_max: int | None
    target_rir: float | None
    sets: list[PublicSetDto]


class AdminSessionExerciseDto(PublicSessionExerciseDto):
    substitution_reason: str | None
    sets: list[AdminSetDto]  # type: ignore[assignment]


class PublicWorkoutSessionDto(StrictDto):
    id: str
    split_day_id: str | None
    session_date_local: date
    started_at: datetime
    completed_at: datetime | None
    status: str
    title: str
    public_visibility: str
    perceived_effort: int | None
    notes_public: str | None = None
    exercises: list[PublicSessionExerciseDto]


class AdminWorkoutSessionDto(PublicWorkoutSessionDto):
    notes_private: str | None
    exercises: list[AdminSessionExerciseDto]  # type: ignore[assignment]


class WaterEntryDto(StrictDto):
    id: str
    amount_ml: int
    occurred_at: datetime


class WaterDayDto(StrictDto):
    local_date: date
    total_ml: int
    goal_ml: int
    progress_ratio: float
    entries: list[WaterEntryDto]


class AchievementDto(StrictDto):
    id: str
    achievement_type: str
    exercise_id: str | None
    title: str
    message: str
    achieved_at: datetime
    public: bool


class PersonalRecordDto(StrictDto):
    id: str
    exercise_id: str
    exercise_name: str
    record_type: str
    value_numeric: float
    unit: str
    reps_context: int | None
    achieved_at: datetime
