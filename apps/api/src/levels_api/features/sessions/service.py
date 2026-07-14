from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from levels_api.errors import ApiError
from levels_api.features.profile.service import require_profile
from levels_api.features.water.service import local_date_for_profile
from levels_api.models import (
    PublicVisibility,
    SessionExercise,
    SessionStatus,
    WorkoutSession,
)
from levels_api.schemas import serialize_admin_session, serialize_public_session

from . import repository
from .schemas import SessionUpdate, StartSession


def require_session(session: Session, session_id: str) -> WorkoutSession:
    workout = repository.session_by_id(session, session_id)
    if workout is None:
        raise ApiError(404, "NOT_FOUND", "The requested workout session was not found.")
    return workout


def start_session(
    session: Session, write: StartSession, idempotency_key: str | None
) -> WorkoutSession:
    if idempotency_key:
        existing = repository.session_by_idempotency_key(session, idempotency_key)
        if existing is not None:
            return existing
    profile = require_profile(session)
    split_day = None
    if write.split_day_id is not None:
        split_day = repository.split_day_by_id(session, write.split_day_id)
        if split_day is None:
            raise ApiError(400, "VALIDATION_ERROR", "The selected split day does not exist.")
    local_date = write.date or local_date_for_profile(profile.timezone)
    workout = WorkoutSession(
        split_day=split_day,
        session_date_local=local_date,
        started_at=datetime.now(UTC),
        completed_at=None,
        status=SessionStatus.IN_PROGRESS,
        title=write.title or (split_day.name if split_day is not None else "Workout"),
        public_visibility=PublicVisibility.PRIVATE,
        perceived_effort=None,
        notes_private=None,
        notes_public=None,
        deleted_at=None,
        idempotency_key=idempotency_key,
    )
    if split_day is not None:
        workout.exercises = [
            SessionExercise(
                exercise=item.exercise,
                source_template_item_id=item.id,
                sequence=item.sequence,
                display_name_snapshot=item.exercise.name,
                variation_group_snapshot=item.exercise.variation_group,
                rep_min_snapshot=item.rep_min,
                rep_max_snapshot=item.rep_max,
                target_rir_snapshot=item.target_rir,
                notes=item.notes,
                substitution_reason=None,
            )
            for item in split_day.items
        ]
    session.add(workout)
    session.flush()
    return workout


def update_session(session: Session, session_id: str, write: SessionUpdate) -> WorkoutSession:
    workout = require_session(session, session_id)
    for field in (
        "title",
        "public_visibility",
        "perceived_effort",
        "notes_private",
        "notes_public",
    ):
        if field in write.model_fields_set:
            setattr(workout, field, getattr(write, field))
    if write.status is not None:
        workout.status = SessionStatus(write.status)
        workout.completed_at = (
            datetime.now(UTC) if workout.status == SessionStatus.COMPLETED else None
        )
    session.flush()
    return workout


def delete_session(session: Session, session_id: str) -> None:
    workout = require_session(session, session_id)
    workout.deleted_at = datetime.now(UTC)


def session_payload(session: Session, workout: WorkoutSession, *, owner: bool) -> dict[str, object]:
    if owner:
        return serialize_admin_session(workout)
    if workout.status != SessionStatus.COMPLETED:
        raise ApiError(404, "NOT_FOUND", "The requested workout session was not found.")
    profile = require_profile(session)
    assert profile.visibility is not None
    payload = serialize_public_session(workout, profile.visibility)
    if payload is None:
        raise ApiError(404, "NOT_FOUND", "The requested workout session was not found.")
    return payload


def list_session_payloads(
    session: Session,
    *,
    owner: bool,
    public_only: bool,
    date_from: date | None,
    date_to: date | None,
    exercise_id: str | None,
) -> list[dict[str, object]]:
    profile = require_profile(session)
    assert profile.visibility is not None
    result: list[dict[str, object]] = []
    for workout in repository.all_sessions(session):
        if date_from is not None and workout.session_date_local < date_from:
            continue
        if date_to is not None and workout.session_date_local > date_to:
            continue
        if exercise_id and not any(item.exercise_id == exercise_id for item in workout.exercises):
            continue
        if owner and not public_only:
            result.append(serialize_admin_session(workout))
            continue
        if workout.status != SessionStatus.COMPLETED:
            continue
        payload = serialize_public_session(workout, profile.visibility)
        if payload is not None:
            result.append(payload)
    return result
