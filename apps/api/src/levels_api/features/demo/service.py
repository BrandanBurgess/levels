from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from levels_api.errors import ApiError
from levels_api.features.avatar.service import serialize_avatar
from levels_api.features.streak.service import streak_summary
from levels_api.models import (
    AvatarSettings,
    Exercise,
    PersonalRecord,
    Profile,
    SessionStatus,
    Split,
    User,
    WorkoutSession,
)
from levels_api.seed.loader import DEMO_EMAIL


def _serialize_exercise(exercise: Exercise) -> dict[str, Any]:
    return {
        "id": exercise.id,
        "scope": "global" if exercise.owner_user_id is None else "custom",
        "can_edit": False,
        "slug": exercise.slug,
        "name": exercise.name,
        "aliases": exercise.aliases,
        "variation_group": exercise.variation_group,
        "movement_pattern": exercise.movement_pattern,
        "equipment": exercise.equipment,
        "measurement_type": exercise.measurement_type.value,
        "compound": exercise.compound,
        "unilateral": exercise.unilateral,
        "default_rep_min": exercise.default_rep_min,
        "default_rep_max": exercise.default_rep_max,
        "default_rest_seconds": exercise.default_rest_seconds,
        "automatic_progression_enabled": exercise.automatic_progression_enabled,
        "muscle_targets": [
            {
                "slug": link.muscle_group.slug,
                "display_name": link.muscle_group.display_name,
                "role": link.role.value,
                "intensity": float(link.contribution),
                "svg_region_ids": link.muscle_group.svg_region_ids,
            }
            for link in exercise.muscle_links
        ],
    }


def _serialize_item(item: Any) -> dict[str, Any]:
    return {
        "id": item.id,
        "exercise": _serialize_exercise(item.exercise),
        "sequence": item.sequence,
        "item_type": item.item_type.value,
        "sets": item.sets,
        "rep_min": item.rep_min,
        "rep_max": item.rep_max,
        "duration_seconds": item.duration_seconds,
        "distance_meters": (
            float(item.distance_meters) if item.distance_meters is not None else None
        ),
        "rounds_target": item.rounds_target,
        "rest_seconds": item.rest_seconds,
        "target_rir": float(item.target_rir) if item.target_rir is not None else None,
        "superset_group": item.superset_group,
        "notes": item.notes,
        "optional": item.optional,
        "alternatives": [
            _serialize_exercise(alternative.exercise) for alternative in item.alternatives
        ],
    }


def _serialize_day(day: Any) -> dict[str, Any]:
    return {
        "id": day.id,
        "name": day.name,
        "day_type": day.day_type,
        "sequence": day.sequence,
        "is_optional": day.is_optional,
        "items": [_serialize_item(item) for item in day.items],
    }


def _serialize_split(split: Split) -> dict[str, Any]:
    return {
        "id": split.id,
        "name": split.name,
        "slug": split.slug,
        "description": split.description,
        "is_active": split.is_active,
        "days": [_serialize_day(day) for day in split.days],
    }


def demo_bootstrap(session: Session) -> dict[str, Any]:
    demo = session.scalar(select(User).where(User.email_normalized == DEMO_EMAIL, User.is_demo))
    if demo is None:
        raise ApiError(503, "DEMO_UNAVAILABLE", "The demo is unavailable.")
    profile = session.scalar(select(Profile).where(Profile.user_id == demo.id))
    avatar = session.get(AvatarSettings, demo.id)
    if profile is None or avatar is None:
        raise ApiError(503, "DEMO_UNAVAILABLE", "The demo is unavailable.")

    splits = (
        session.scalars(
            select(Split)
            .where(Split.user_id == demo.id, Split.archived_at.is_(None))
            .order_by(Split.display_order)
        )
        .unique()
        .all()
    )
    active_split = next((split for split in splits if split.is_active), None)
    effective_day = active_split.days[0] if active_split and active_split.days else None
    exercise_plan = [
        {
            "id": item.id,
            "source_template_item_id": item.id,
            "exercise": _serialize_exercise(item.exercise),
            "sequence": item.sequence,
            "item_type": item.item_type.value,
            "planned_sets": item.sets,
            "rep_min": item.rep_min,
            "rep_max": item.rep_max,
            "duration_seconds": item.duration_seconds,
            "distance_meters": (
                float(item.distance_meters) if item.distance_meters is not None else None
            ),
            "rounds_target": item.rounds_target,
            "rest_seconds": item.rest_seconds,
            "target_rir": float(item.target_rir) if item.target_rir is not None else None,
            "superset_group": item.superset_group,
            "optional": item.optional,
            "notes": item.notes,
        }
        for item in (effective_day.items if effective_day is not None else [])
    ]
    target_by_slug: dict[str, dict[str, Any]] = {}
    role_rank = {"stabilizer": 0, "secondary": 1, "primary": 2}
    effective_items = effective_day.items if effective_day is not None else []
    for item in effective_items:
        for target in _serialize_exercise(item.exercise)["muscle_targets"]:
            existing = target_by_slug.get(target["slug"])
            if existing is None or role_rank[target["role"]] > role_rank[existing["role"]]:
                target_by_slug[target["slug"]] = target

    sessions = (
        session.scalars(
            select(WorkoutSession)
            .where(
                WorkoutSession.user_id == demo.id,
                WorkoutSession.status == SessionStatus.COMPLETED,
                WorkoutSession.deleted_at.is_(None),
            )
            .order_by(WorkoutSession.session_date_local.desc())
            .limit(5)
        )
        .unique()
        .all()
    )
    records = session.scalars(
        select(PersonalRecord).where(PersonalRecord.user_id == demo.id, PersonalRecord.is_current)
    ).all()
    public_profile = {
        "display_name": profile.display_name,
        "height_cm": profile.height_cm,
        "body_weight_kg": (
            float(profile.body_weight_kg) if profile.body_weight_kg is not None else None
        ),
        "preferred_units": profile.preferred_units.value,
        "timezone": profile.timezone,
    }
    streak = streak_summary(session, demo.id)
    avatar_payload = serialize_avatar(avatar)
    return {
        "mode": "demo",
        "profile": public_profile,
        "today": {
            "local_date": date.today().isoformat(),
            "profile": public_profile,
            "effective_day": _serialize_day(effective_day) if effective_day else None,
            "exercise_plan": exercise_plan,
            "muscle_targets": list(target_by_slug.values()),
            "avatar": avatar_payload,
            "streak": streak,
        },
        "avatar": avatar_payload,
        "splits": [_serialize_split(split) for split in splits],
        "exercises": [
            _serialize_exercise(exercise)
            for exercise in session.scalars(
                select(Exercise)
                .where(Exercise.owner_user_id.is_(None), Exercise.archived_at.is_(None))
                .order_by(Exercise.name)
                .limit(24)
            ).unique()
        ],
        "journal_samples": [
            {
                "id": workout.id,
                "session_date_local": workout.session_date_local.isoformat(),
                "title": workout.title,
                "completed_at": workout.completed_at.isoformat()
                if workout.completed_at
                else workout.started_at.isoformat(),
                "exercises_completed": len(
                    [exercise for exercise in workout.exercises if exercise.removed_at is None]
                ),
            }
            for workout in sessions
        ],
        "progress": {
            "completed_sessions": session.scalar(
                select(func.count())
                .select_from(WorkoutSession)
                .where(
                    WorkoutSession.user_id == demo.id,
                    WorkoutSession.status == SessionStatus.COMPLETED,
                    WorkoutSession.deleted_at.is_(None),
                )
            )
            or 0,
            "current_records": [
                {
                    "id": record.id,
                    "exercise_id": record.exercise_id,
                    "exercise_name": record.exercise.name,
                    "record_type": record.record_type.value,
                    "value_numeric": float(record.value_numeric),
                    "unit": record.unit,
                    "reps_context": record.reps_context,
                    "achieved_at": record.achieved_at.isoformat(),
                }
                for record in records
            ],
        },
        "streak": streak,
    }
