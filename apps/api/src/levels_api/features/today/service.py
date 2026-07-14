from __future__ import annotations

from datetime import date
from typing import cast

from sqlalchemy.orm import Session

from levels_api.features.profile.service import require_profile
from levels_api.features.water.service import water_day
from levels_api.models import Exercise, ExerciseMuscle, MuscleRole, SplitDay, WorkoutTemplateItem
from levels_api.schemas import (
    serialize_admin_session,
    serialize_public_achievements,
    serialize_public_profile,
    serialize_public_session,
)

from . import repository


def _muscle_target(link: ExerciseMuscle) -> dict[str, object]:
    muscle = link.muscle_group
    return {
        "slug": muscle.slug,
        "display_name": muscle.display_name,
        "role": link.role.value,
        "intensity": float(link.contribution),
        "svg_region_ids": muscle.svg_region_ids,
    }


def _exercise(exercise: Exercise) -> dict[str, object]:
    return {
        "id": exercise.id,
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
        "muscle_targets": [_muscle_target(link) for link in exercise.muscle_links],
    }


def _template_item(item: WorkoutTemplateItem) -> dict[str, object]:
    return {
        "id": item.id,
        "exercise": _exercise(item.exercise),
        "sequence": item.sequence,
        "item_type": item.item_type.value,
        "sets": item.sets,
        "rep_min": item.rep_min,
        "rep_max": item.rep_max,
        "rest_seconds": item.rest_seconds,
        "target_rir": float(item.target_rir) if item.target_rir is not None else None,
        "superset_group": item.superset_group,
        "notes": item.notes,
        "optional": item.optional,
        "alternatives": [_exercise(alternative.exercise) for alternative in item.alternatives],
    }


def serialize_scheduled_day(day: SplitDay | None) -> dict[str, object] | None:
    if day is None:
        return None
    return {
        "id": day.id,
        "name": day.name,
        "day_type": day.day_type,
        "sequence": day.sequence,
        "is_optional": day.is_optional,
        "items": [_template_item(item) for item in day.items],
    }


def aggregate_muscle_targets(day: SplitDay | None) -> list[dict[str, object]]:
    if day is None:
        return []
    strongest: dict[str, ExerciseMuscle] = {}
    rank = {MuscleRole.STABILIZER: 0, MuscleRole.SECONDARY: 1, MuscleRole.PRIMARY: 2}
    for item in day.items:
        for link in item.exercise.muscle_links:
            current = strongest.get(link.muscle_group_id)
            if current is None or rank[link.role] > rank[current.role]:
                strongest[link.muscle_group_id] = link
    return sorted(
        (_muscle_target(link) for link in strongest.values()),
        key=lambda target: (
            -cast(float, target["intensity"]),
            str(target["display_name"]),
        ),
    )


def dashboard(session: Session, local_date: date, *, owner: bool) -> dict[str, object]:
    profile = require_profile(session)
    assert profile.settings is not None and profile.visibility is not None
    day = repository.scheduled_day(session, profile.settings.active_split_id, local_date.weekday())
    active = repository.active_session(session, local_date)
    active_payload = None
    if active is not None:
        active_payload = (
            serialize_admin_session(active)
            if owner
            else serialize_public_session(active, profile.visibility)
        )
    return {
        "date": local_date.isoformat(),
        "profile": serialize_public_profile(profile),
        "scheduled_day": serialize_scheduled_day(day),
        "active_session": active_payload,
        "muscle_targets": aggregate_muscle_targets(day),
        "water": (
            water_day(session, local_date) if owner or profile.visibility.show_water else None
        ),
        "latest_achievements": serialize_public_achievements(
            repository.latest_achievements(session)
        ),
    }
