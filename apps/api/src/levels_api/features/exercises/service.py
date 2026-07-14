from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from levels_api.errors import ApiError
from levels_api.models import Exercise, ExerciseMuscle, MuscleGroup

from . import repository
from .schemas import ExerciseWrite


def serialize_exercise(exercise: Exercise) -> dict[str, object]:
    targets = sorted(
        (
            {
                "slug": link.muscle_group.slug,
                "display_name": link.muscle_group.display_name,
                "role": link.role.value,
                "intensity": float(link.contribution),
                "svg_region_ids": link.muscle_group.svg_region_ids,
            }
            for link in exercise.muscle_links
        ),
        key=lambda target: (str(target["role"]), str(target["display_name"])),
    )
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
        "muscle_targets": targets,
    }


def search_exercises(
    session: Session,
    *,
    query: str | None = None,
    primary_muscle: str | None = None,
    secondary_muscle: str | None = None,
    body_region: str | None = None,
    movement_pattern: str | None = None,
    equipment: str | None = None,
    unilateral: bool | None = None,
    include_archived: bool = False,
) -> list[dict[str, object]]:
    matches: list[Exercise] = []
    needle = query.casefold().strip() if query else None
    for exercise in repository.all_exercises(session):
        if exercise.archived_at is not None and not include_archived:
            continue
        if (
            needle
            and needle not in exercise.name.casefold()
            and not any(needle in alias.casefold() for alias in exercise.aliases)
        ):
            continue
        if movement_pattern and exercise.movement_pattern != movement_pattern:
            continue
        if equipment and exercise.equipment != equipment:
            continue
        if unilateral is not None and exercise.unilateral is not unilateral:
            continue
        links = exercise.muscle_links
        if primary_muscle and not any(
            link.role.value == "primary" and link.muscle_group.slug == primary_muscle
            for link in links
        ):
            continue
        if secondary_muscle and not any(
            link.role.value == "secondary" and link.muscle_group.slug == secondary_muscle
            for link in links
        ):
            continue
        if body_region and not any(link.muscle_group.body_region == body_region for link in links):
            continue
        matches.append(exercise)
    return [serialize_exercise(exercise) for exercise in matches]


def require_exercise(session: Session, exercise_id: str) -> Exercise:
    exercise = repository.exercise_by_id(session, exercise_id)
    if exercise is None:
        raise ApiError(404, "NOT_FOUND", "The requested exercise was not found.")
    return exercise


def _apply_write(session: Session, exercise: Exercise, write: ExerciseWrite) -> None:
    existing = repository.exercise_by_slug(session, write.slug)
    if existing is not None and existing.id != exercise.id:
        raise ApiError(409, "SLUG_CONFLICT", "An exercise already uses this slug.")
    slugs = {target.slug for target in write.muscle_targets}
    groups = {
        group.slug: group
        for group in session.scalars(select(MuscleGroup).where(MuscleGroup.slug.in_(slugs)))
    }
    missing = sorted(slugs - groups.keys())
    if missing:
        raise ApiError(
            400,
            "VALIDATION_ERROR",
            "One or more muscle targets are unknown.",
            {"muscle_targets": f"Unknown muscle slugs: {', '.join(missing)}"},
        )
    exercise.name = write.name
    exercise.slug = write.slug
    exercise.aliases = write.aliases
    exercise.variation_group = write.variation_group
    exercise.movement_pattern = write.movement_pattern
    exercise.equipment = write.equipment
    exercise.measurement_type = write.measurement_type
    exercise.compound = write.compound
    exercise.unilateral = write.unilateral
    exercise.default_rep_min = write.default_rep_min
    exercise.default_rep_max = write.default_rep_max
    exercise.default_rest_seconds = write.default_rest_seconds
    exercise.automatic_progression_enabled = write.automatic_progression_enabled
    if exercise.muscle_links:
        exercise.muscle_links.clear()
        session.flush()
    exercise.muscle_links = [
        ExerciseMuscle(
            muscle_group=groups[target.slug], role=target.role, contribution=target.intensity
        )
        for target in write.muscle_targets
    ]


def create_exercise(session: Session, write: ExerciseWrite) -> Exercise:
    exercise = Exercise(metadata_json={}, archived_at=None)
    session.add(exercise)
    _apply_write(session, exercise, write)
    session.flush()
    return require_exercise(session, exercise.id)


def update_exercise(session: Session, exercise_id: str, write: ExerciseWrite) -> Exercise:
    exercise = require_exercise(session, exercise_id)
    _apply_write(session, exercise, write)
    session.flush()
    return require_exercise(session, exercise.id)


def archive_exercise(session: Session, exercise_id: str) -> None:
    exercise = require_exercise(session, exercise_id)
    exercise.archived_at = datetime.now(UTC)
