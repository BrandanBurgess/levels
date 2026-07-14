from __future__ import annotations

import re
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from levels_api.errors import ApiError
from levels_api.features.profile.service import require_profile
from levels_api.features.today.service import serialize_scheduled_day
from levels_api.models import (
    Exercise,
    Split,
    SplitDay,
    TemplateAlternative,
    WorkoutTemplateItem,
)

from . import repository
from .schemas import SplitDayWrite, SplitItemWrite, SplitWrite


def serialize_split(split: Split) -> dict[str, object]:
    return {
        "id": split.id,
        "name": split.name,
        "slug": split.slug,
        "description": split.description,
        "is_active": split.is_active,
        "days": [serialize_scheduled_day(day) for day in split.days],
    }


def list_splits(session: Session) -> list[dict[str, object]]:
    return [serialize_split(split) for split in repository.all_splits(session)]


def require_split(session: Session, split_id: str) -> Split:
    split = repository.split_by_id(session, split_id)
    if split is None:
        raise ApiError(404, "NOT_FOUND", "The requested split was not found.")
    return split


def _slug(name: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
    return value or "training-split"


def _exercise_map(session: Session, days: list[SplitDayWrite]) -> dict[str, Exercise]:
    exercise_ids = {
        exercise_id
        for day in days
        for item in day.items
        for exercise_id in [item.exercise_id, *item.alternative_exercise_ids]
    }
    exercises = {
        exercise.id: exercise
        for exercise in session.scalars(select(Exercise).where(Exercise.id.in_(exercise_ids)))
    }
    missing = sorted(exercise_ids - exercises.keys())
    if missing:
        raise ApiError(
            400,
            "VALIDATION_ERROR",
            "One or more template exercises do not exist.",
            {"days": f"Unknown exercise IDs: {', '.join(missing)}"},
        )
    return exercises


def _reconcile_item(
    item: WorkoutTemplateItem,
    write: SplitItemWrite,
    exercises: dict[str, Exercise],
) -> None:
    item.exercise = exercises[write.exercise_id]
    item.sequence = write.sequence
    item.item_type = write.item_type
    item.sets = write.sets
    item.rep_min = write.rep_min
    item.rep_max = write.rep_max
    item.duration_seconds = None
    item.distance_meters = None
    item.rest_seconds = write.rest_seconds
    item.target_rir = write.target_rir
    item.superset_group = None
    item.notes = None
    item.optional = write.optional
    item.alternatives = [
        TemplateAlternative(exercise=exercises[exercise_id], sequence=index)
        for index, exercise_id in enumerate(write.alternative_exercise_ids, start=1)
    ]


def _reconcile_days(session: Session, split: Split, days: list[SplitDayWrite]) -> None:
    exercises = _exercise_map(session, days)
    existing_days = {day.id: day for day in split.days}
    for day_index, day in enumerate(split.days, start=1):
        day.sequence = -day_index
        for item_index, item in enumerate(day.items, start=1):
            item.sequence = -item_index
            item.alternatives.clear()
    session.flush()

    reconciled_days: list[SplitDay] = []
    for day_write in sorted(days, key=lambda value: value.sequence):
        if day_write.id is not None:
            matched_day = existing_days.get(day_write.id)
            if matched_day is None:
                raise ApiError(400, "VALIDATION_ERROR", "A split day ID is invalid.")
            del existing_days[day_write.id]
            day = matched_day
        else:
            day = SplitDay(recommended_weekday=None, description=None)
        existing_items = {item.id: item for item in day.items}
        reconciled_items: list[WorkoutTemplateItem] = []
        for item_write in sorted(day_write.items, key=lambda value: value.sequence):
            if item_write.id is not None:
                matched_item = existing_items.get(item_write.id)
                if matched_item is None:
                    raise ApiError(400, "VALIDATION_ERROR", "A template item ID is invalid.")
                del existing_items[item_write.id]
                item = matched_item
            else:
                item = WorkoutTemplateItem()
            _reconcile_item(item, item_write, exercises)
            reconciled_items.append(item)
        day.name = day_write.name
        day.day_type = day_write.day_type
        day.sequence = day_write.sequence
        day.is_optional = day_write.is_optional
        day.items = reconciled_items
        reconciled_days.append(day)
    split.days = reconciled_days


def _apply_write(session: Session, split: Split, write: SplitWrite, *, creating: bool) -> None:
    slug = write.slug or (_slug(write.name) if creating else split.slug)
    existing = repository.split_by_slug(session, slug)
    if existing is not None and existing.id != split.id:
        raise ApiError(409, "SLUG_CONFLICT", "A split already uses this slug.")
    split.name = write.name
    split.slug = slug
    split.description = write.description
    if write.days is not None:
        _reconcile_days(session, split, write.days)


def create_split(session: Session, write: SplitWrite) -> Split:
    order = session.scalar(select(func.coalesce(func.max(Split.display_order), -1)))
    split = Split(
        is_active=False,
        is_seeded=False,
        display_order=int(order or 0) + 1,
        archived_at=None,
    )
    session.add(split)
    _apply_write(session, split, write, creating=True)
    session.flush()
    return split


def update_split(session: Session, split_id: str, write: SplitWrite) -> Split:
    split = require_split(session, split_id)
    _apply_write(session, split, write, creating=False)
    session.flush()
    return split


def activate_split(session: Session, split_id: str) -> Split:
    target = require_split(session, split_id)
    for split in repository.all_splits(session):
        split.is_active = split.id == target.id
    profile = require_profile(session)
    assert profile.settings is not None
    profile.settings.active_split_id = target.id
    session.flush()
    return target


def archive_split(session: Session, split_id: str) -> None:
    split = require_split(session, split_id)
    if split.is_active:
        raise ApiError(409, "ACTIVE_SPLIT", "Activate another split before archiving this one.")
    split.archived_at = datetime.now(UTC)
