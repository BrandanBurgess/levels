from __future__ import annotations

from datetime import date
from typing import Any

from levels_api.models import (
    Achievement,
    PersonalRecord,
    Profile,
    SessionExercise,
    SetLog,
    VisibilitySettings,
    WaterLog,
    WorkoutSession,
)

from .dtos import (
    AchievementDto,
    AdminProfileDto,
    AdminSessionExerciseDto,
    AdminSetDto,
    AdminWorkoutSessionDto,
    PersonalRecordDto,
    PublicProfileDto,
    PublicSessionExerciseDto,
    PublicSetDto,
    PublicWorkoutSessionDto,
    SettingsDto,
    VisibilityDto,
    WaterDayDto,
    WaterEntryDto,
)

JsonObject = dict[str, Any]


def _dump(dto: object, *, exclude_none: bool = False) -> JsonObject:
    return dto.model_dump(mode="json", exclude_none=exclude_none)  # type: ignore[attr-defined,no-any-return]


def serialize_public_profile(profile: Profile) -> JsonObject:
    visibility = profile.visibility
    dto = PublicProfileDto(
        display_name=profile.display_name,
        height_cm=profile.height_cm if visibility and visibility.show_height else None,
        body_weight_kg=(
            float(profile.body_weight_kg)
            if visibility and visibility.show_body_weight and profile.body_weight_kg is not None
            else None
        ),
        preferred_units=profile.preferred_units.value,
        timezone=profile.timezone,
        avatar_variant=profile.avatar_variant,
    )
    return _dump(dto, exclude_none=True)


def serialize_admin_profile(profile: Profile) -> JsonObject:
    return _dump(
        AdminProfileDto(
            id=profile.id,
            display_name=profile.display_name,
            height_cm=profile.height_cm,
            body_weight_kg=(
                float(profile.body_weight_kg) if profile.body_weight_kg is not None else None
            ),
            preferred_units=profile.preferred_units.value,
            timezone=profile.timezone,
            avatar_variant=profile.avatar_variant,
        )
    )


def serialize_settings(profile: Profile) -> JsonObject:
    if profile.settings is None or profile.visibility is None:
        raise ValueError("Profile settings and visibility must be loaded")
    settings = profile.settings
    visibility = profile.visibility
    return _dump(
        SettingsDto(
            active_split_id=settings.active_split_id,
            week_starts_on=settings.week_starts_on,
            default_water_goal_ml=settings.default_water_goal_ml,
            water_quick_add_ml=settings.water_quick_add_ml,
            default_target_rir=float(settings.default_target_rir),
            default_load_increment_kg=float(settings.default_load_increment_kg),
            reduced_motion_override=settings.reduced_motion_override,
            visibility=VisibilityDto(
                show_height=visibility.show_height,
                show_body_weight=visibility.show_body_weight,
                show_water=visibility.show_water,
                show_session_summaries=visibility.show_session_summaries,
                show_set_details=visibility.show_set_details,
                show_public_notes=visibility.show_public_notes,
                show_progress_charts=visibility.show_progress_charts,
                show_personal_records=visibility.show_personal_records,
                show_readiness=visibility.show_readiness,
            ),
        )
    )


def _public_set(set_log: SetLog) -> PublicSetDto:
    return PublicSetDto(
        id=set_log.id,
        sequence=set_log.sequence,
        set_type=set_log.set_type.value,
        load_kg=float(set_log.load_kg) if set_log.load_kg is not None else None,
        reps=set_log.reps,
        rir=float(set_log.rir) if set_log.rir is not None else None,
        duration_seconds=set_log.duration_seconds,
        distance_meters=(
            float(set_log.distance_meters) if set_log.distance_meters is not None else None
        ),
        rounds=set_log.rounds,
        form_quality=set_log.form_quality,
        pain_flag=set_log.pain_flag,
        completed_at=set_log.completed_at,
    )


def _admin_set(set_log: SetLog) -> AdminSetDto:
    public = _public_set(set_log)
    return AdminSetDto(**public.model_dump(), notes=set_log.notes)


def serialize_admin_set(set_log: SetLog) -> JsonObject:
    return _dump(_admin_set(set_log))


def serialize_admin_session_exercise(session_exercise: SessionExercise) -> JsonObject:
    return _dump(_admin_exercise(session_exercise))


def _public_exercise(
    session_exercise: SessionExercise, *, include_sets: bool
) -> PublicSessionExerciseDto:
    return PublicSessionExerciseDto(
        id=session_exercise.id,
        exercise_id=session_exercise.exercise_id,
        display_name=session_exercise.display_name_snapshot,
        variation_group=session_exercise.variation_group_snapshot,
        sequence=session_exercise.sequence,
        rep_min=session_exercise.rep_min_snapshot,
        rep_max=session_exercise.rep_max_snapshot,
        target_rir=(
            float(session_exercise.target_rir_snapshot)
            if session_exercise.target_rir_snapshot is not None
            else None
        ),
        sets=[
            _public_set(set_log) for set_log in session_exercise.sets if set_log.deleted_at is None
        ]
        if include_sets
        else [],
    )


def _admin_exercise(session_exercise: SessionExercise) -> AdminSessionExerciseDto:
    public = _public_exercise(session_exercise, include_sets=False)
    values = public.model_dump(exclude={"sets"})
    return AdminSessionExerciseDto(
        **values,
        substitution_reason=session_exercise.substitution_reason,
        sets=[
            _admin_set(set_log) for set_log in session_exercise.sets if set_log.deleted_at is None
        ],
    )


def _session_values(session: WorkoutSession) -> JsonObject:
    return {
        "id": session.id,
        "split_day_id": session.split_day_id,
        "session_date_local": session.session_date_local,
        "started_at": session.started_at,
        "completed_at": session.completed_at,
        "status": session.status.value,
        "title": session.title,
        "public_visibility": session.public_visibility.value,
        "perceived_effort": session.perceived_effort,
    }


def serialize_public_session(
    session: WorkoutSession, visibility: VisibilitySettings
) -> JsonObject | None:
    if not visibility.show_session_summaries or session.public_visibility.value == "private":
        return None
    show_full = session.public_visibility.value == "full"
    dto = PublicWorkoutSessionDto(
        **_session_values(session),
        notes_public=session.notes_public if visibility.show_public_notes else None,
        exercises=(
            [
                _public_exercise(session_exercise, include_sets=visibility.show_set_details)
                for session_exercise in session.exercises
            ]
            if show_full
            else []
        ),
    )
    return _dump(dto, exclude_none=True)


def serialize_admin_session(session: WorkoutSession) -> JsonObject:
    dto = AdminWorkoutSessionDto(
        **_session_values(session),
        notes_public=session.notes_public,
        notes_private=session.notes_private,
        exercises=[_admin_exercise(item) for item in session.exercises],
    )
    return _dump(dto)


def serialize_water_day(local_date: date, entries: list[WaterLog], goal_ml: int) -> JsonObject:
    total_ml = sum(entry.amount_ml for entry in entries)
    return _dump(
        WaterDayDto(
            local_date=local_date,
            total_ml=total_ml,
            goal_ml=goal_ml,
            progress_ratio=total_ml / goal_ml,
            entries=[
                WaterEntryDto(id=entry.id, amount_ml=entry.amount_ml, occurred_at=entry.occurred_at)
                for entry in entries
            ],
        )
    )


def serialize_public_achievements(achievements: list[Achievement]) -> list[JsonObject]:
    return [
        _dump(
            AchievementDto(
                id=achievement.id,
                achievement_type=achievement.achievement_type,
                exercise_id=achievement.exercise_id,
                title=achievement.title,
                message=achievement.message,
                achieved_at=achievement.achieved_at,
                public=achievement.public,
            )
        )
        for achievement in achievements
        if achievement.public
    ]


def serialize_personal_record(record: PersonalRecord) -> JsonObject:
    return _dump(
        PersonalRecordDto(
            id=record.id,
            exercise_id=record.exercise_id,
            exercise_name=record.exercise.name,
            record_type=record.record_type.value,
            value_numeric=float(record.value_numeric),
            unit=record.unit,
            reps_context=record.reps_context,
            achieved_at=record.achieved_at,
        )
    )
