from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from levels_api.errors import ApiError
from levels_api.features.profile.service import require_profile
from levels_api.features.water.service import local_date_for_profile
from levels_api.models import (
    MeasurementType,
    PublicVisibility,
    SessionExercise,
    SessionStatus,
    SetLog,
    WorkoutSession,
)
from levels_api.schemas import serialize_admin_session, serialize_public_session
from levels_api.schemas.serializers import (
    serialize_admin_session_exercise,
    serialize_admin_set,
)

from . import repository
from .schemas import AddSessionExercise, SessionUpdate, SetWrite, StartSession


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


def _require_mutable(workout: WorkoutSession) -> None:
    if workout.status == SessionStatus.CANCELLED:
        raise ApiError(409, "SESSION_CANCELLED", "A cancelled session cannot be changed.")


def add_or_substitute_exercise(
    session: Session, session_id: str, write: AddSessionExercise
) -> SessionExercise:
    workout = require_session(session, session_id)
    _require_mutable(workout)
    exercise = repository.exercise_by_id(session, write.exercise_id)
    if exercise is None:
        raise ApiError(400, "VALIDATION_ERROR", "The selected exercise does not exist.")

    if write.replace_session_exercise_id is not None:
        item = repository.session_exercise_by_id(session, write.replace_session_exercise_id)
        if item is None or item.workout_session_id != workout.id:
            raise ApiError(
                400, "VALIDATION_ERROR", "The exercise to replace is not in this session."
            )
        if item.sets:
            raise ApiError(
                409,
                "EXERCISE_HAS_SETS",
                "Remove existing sets before substituting this exercise.",
            )
        item.exercise = exercise
        item.display_name_snapshot = exercise.name
        item.variation_group_snapshot = exercise.variation_group
        item.rep_min_snapshot = exercise.default_rep_min
        item.rep_max_snapshot = exercise.default_rep_max
        item.substitution_reason = write.substitution_reason
        session.flush()
        return item

    sequence = write.sequence or max((item.sequence for item in workout.exercises), default=0) + 1
    if any(item.sequence == sequence for item in workout.exercises):
        raise ApiError(400, "VALIDATION_ERROR", "That exercise sequence is already in use.")
    item = SessionExercise(
        workout_session=workout,
        exercise=exercise,
        source_template_item_id=None,
        sequence=sequence,
        display_name_snapshot=exercise.name,
        variation_group_snapshot=exercise.variation_group,
        rep_min_snapshot=exercise.default_rep_min,
        rep_max_snapshot=exercise.default_rep_max,
        target_rir_snapshot=None,
        notes=None,
        substitution_reason=write.substitution_reason,
    )
    session.add(item)
    session.flush()
    return item


def exercise_payload(item: SessionExercise) -> dict[str, object]:
    return serialize_admin_session_exercise(item)


def _require_session_exercise(
    session: Session, workout: WorkoutSession, item_id: str
) -> SessionExercise:
    item = repository.session_exercise_by_id(session, item_id)
    if item is None or item.workout_session_id != workout.id:
        raise ApiError(400, "VALIDATION_ERROR", "The selected exercise is not in this session.")
    return item


def _validate_measurement(item: SessionExercise, write: SetWrite) -> None:
    measurement = item.exercise.measurement_type
    required = {
        MeasurementType.LOAD_REPS: (write.load_kg, write.reps, "load_kg and reps"),
        MeasurementType.BODYWEIGHT_REPS: (write.reps, write.reps, "reps"),
        MeasurementType.DURATION: (
            write.duration_seconds,
            write.duration_seconds,
            "duration_seconds",
        ),
        MeasurementType.DISTANCE: (write.distance_meters, write.distance_meters, "distance_meters"),
        MeasurementType.ROUNDS: (write.rounds, write.rounds, "rounds"),
    }[measurement]
    if required[0] is None or required[1] is None:
        raise ApiError(
            400,
            "VALIDATION_ERROR",
            f"{required[2]} must be provided for a {measurement.value} exercise.",
        )


def _apply_set_write(set_log: SetLog, write: SetWrite) -> None:
    for field in (
        "set_type",
        "load_kg",
        "reps",
        "rir",
        "duration_seconds",
        "distance_meters",
        "rounds",
        "bodyweight_assistance_kg",
        "form_quality",
        "pain_flag",
        "notes",
    ):
        value = getattr(write, field)
        if field in {"load_kg", "rir", "distance_meters", "bodyweight_assistance_kg"}:
            value = Decimal(str(value)) if value is not None else None
        setattr(set_log, field, value)


def create_set(
    session: Session, session_id: str, write: SetWrite, idempotency_key: str | None
) -> SetLog:
    workout = require_session(session, session_id)
    _require_mutable(workout)
    if idempotency_key:
        existing = repository.set_by_idempotency_key(session, idempotency_key)
        if existing is not None:
            if existing.session_exercise.workout_session_id != workout.id:
                raise ApiError(
                    409, "IDEMPOTENCY_CONFLICT", "That idempotency key is already in use."
                )
            return existing
    item = _require_session_exercise(session, workout, write.session_exercise_id)
    _validate_measurement(item, write)
    sequence = write.sequence or max((set_log.sequence for set_log in item.sets), default=0) + 1
    if any(set_log.sequence == sequence for set_log in item.sets):
        raise ApiError(400, "VALIDATION_ERROR", "That set sequence is already in use.")
    set_log = SetLog(
        session_exercise=item,
        sequence=sequence,
        completed_at=datetime.now(UTC),
        deleted_at=None,
        idempotency_key=idempotency_key,
    )
    _apply_set_write(set_log, write)
    session.add(set_log)
    session.flush()
    return set_log


def update_set(session: Session, set_id: str, write: SetWrite) -> SetLog:
    set_log = repository.set_by_id(session, set_id)
    if set_log is None:
        raise ApiError(404, "NOT_FOUND", "The requested set was not found.")
    workout = set_log.session_exercise.workout_session
    _require_mutable(workout)
    if write.session_exercise_id != set_log.session_exercise_id:
        raise ApiError(400, "VALIDATION_ERROR", "A set cannot be moved to another exercise.")
    _validate_measurement(set_log.session_exercise, write)
    if write.sequence is not None and write.sequence != set_log.sequence:
        all_sets = set_log.session_exercise.sets
        if any(item.id != set_log.id and item.sequence == write.sequence for item in all_sets):
            raise ApiError(400, "VALIDATION_ERROR", "That set sequence is already in use.")
        set_log.sequence = write.sequence
    _apply_set_write(set_log, write)
    session.flush()
    return set_log


def delete_set(session: Session, set_id: str) -> None:
    set_log = repository.set_by_id(session, set_id)
    if set_log is None:
        raise ApiError(404, "NOT_FOUND", "The requested set was not found.")
    _require_mutable(set_log.session_exercise.workout_session)
    set_log.deleted_at = datetime.now(UTC)


def set_write_payload(set_log: SetLog) -> dict[str, object]:
    return {
        "set": serialize_admin_set(set_log),
        "new_achievements": [],
        "affected_records": [],
    }
