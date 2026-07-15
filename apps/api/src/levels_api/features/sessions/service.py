from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from levels_api.errors import ApiError
from levels_api.features.records.engine import RecordResult, rebuild_records
from levels_api.features.today import repository as today_repository
from levels_api.features.today.service import (
    exercise_plan_payload,
    record_receipt,
    replay_receipt,
    require_schedule,
    resolve_effective_plan,
)
from levels_api.models import (
    MeasurementType,
    PublicVisibility,
    SessionExercise,
    SessionStatus,
    SetLog,
    TemplateItemType,
    WorkoutSession,
)
from levels_api.schemas.serializers import (
    serialize_admin_set,
    serialize_personal_record,
    serialize_public_achievements,
)

from . import repository
from .schemas import (
    AddSessionExercise,
    ReorderSessionExercises,
    SessionExerciseUpdate,
    SessionUpdate,
    SetWrite,
    StartSession,
)


def require_session(session: Session, user_id: str, session_id: str) -> WorkoutSession:
    workout = repository.session_by_id(session, user_id, session_id)
    if workout is None:
        raise ApiError(404, "NOT_FOUND", "The requested workout session was not found.")
    return workout


def _version(workout: WorkoutSession, expected: int) -> None:
    if workout.version != expected:
        raise ApiError(409, "VERSION_CONFLICT", "The session changed. Refresh and try again.")


def _require_mutable(workout: WorkoutSession) -> None:
    if workout.status in {SessionStatus.CANCELLED, SessionStatus.COMPLETED}:
        raise ApiError(
            409,
            "SESSION_IMMUTABLE",
            "A completed or cancelled session cannot be changed.",
        )


def _set_payload(set_log: SetLog) -> dict[str, object]:
    return {
        "id": set_log.id,
        "sequence": set_log.sequence,
        "set_type": set_log.set_type.value,
        "load_kg": float(set_log.load_kg) if set_log.load_kg is not None else None,
        "reps": set_log.reps,
        "rir": float(set_log.rir) if set_log.rir is not None else None,
        "duration_seconds": set_log.duration_seconds,
        "distance_meters": (
            float(set_log.distance_meters) if set_log.distance_meters is not None else None
        ),
        "rounds": set_log.rounds,
        "form_quality": set_log.form_quality,
        "pain_flag": set_log.pain_flag,
        "completed_at": _iso_datetime(set_log.completed_at),
        "notes": set_log.notes,
    }


def exercise_payload(item: SessionExercise) -> dict[str, object]:
    return {
        "id": item.id,
        "exercise_id": item.exercise_id,
        "source_template_item_id": item.source_template_item_id,
        "display_name": item.display_name_snapshot,
        "variation_group": item.variation_group_snapshot,
        "sequence": item.sequence,
        "planned_sets": item.planned_sets,
        "item_type": item.item_type.value,
        "rep_min": item.rep_min_snapshot,
        "rep_max": item.rep_max_snapshot,
        "duration_seconds": item.duration_seconds_snapshot,
        "distance_meters": (
            float(item.distance_meters_snapshot)
            if item.distance_meters_snapshot is not None
            else None
        ),
        "rounds_target": item.rounds_target_snapshot,
        "rest_seconds": item.rest_seconds_snapshot,
        "target_rir": (
            float(item.target_rir_snapshot) if item.target_rir_snapshot is not None else None
        ),
        "optional": item.optional_snapshot,
        "notes": item.notes,
        "substitution_reason": item.substitution_reason,
        "removed_at": _iso_datetime(item.removed_at) if item.removed_at is not None else None,
        "removal_reason": item.removal_reason,
        "sets": [_set_payload(row) for row in item.sets if row.deleted_at is None],
    }


def _iso_datetime(value: datetime) -> str:
    return value.replace(tzinfo=value.tzinfo or UTC).isoformat()


def session_payload(workout: WorkoutSession) -> dict[str, object]:
    return {
        "id": workout.id,
        "version": workout.version,
        "split_day_id": workout.split_day_id,
        "session_date_local": workout.session_date_local.isoformat(),
        "started_at": _iso_datetime(workout.started_at),
        "completed_at": _iso_datetime(workout.completed_at) if workout.completed_at else None,
        "status": workout.status.value,
        "title": workout.title,
        "perceived_effort": workout.perceived_effort,
        "notes_private": workout.notes_private,
        "exercises": [
            exercise_payload(item)
            for item in sorted(workout.exercises, key=lambda row: row.sequence)
        ],
    }


def list_session_payloads(
    session: Session,
    user_id: str,
    *,
    date_from: date | None,
    date_to: date | None,
    exercise_id: str | None,
) -> list[dict[str, object]]:
    return [
        session_payload(workout)
        for workout in repository.all_sessions(
            session,
            user_id,
            date_from=date_from,
            date_to=date_to,
            exercise_id=exercise_id,
        )
    ]


def _snapshot_from_plan_item(workout: WorkoutSession, item: dict[str, object]) -> SessionExercise:
    exercise = item["exercise"]
    assert isinstance(exercise, dict)
    return SessionExercise(
        workout_session=workout,
        exercise_id=str(exercise["id"]),
        source_template_item_id=(
            str(item["source_template_item_id"])
            if item.get("source_template_item_id") is not None
            else None
        ),
        sequence=cast(int, item["sequence"]),
        planned_sets=cast(int, item["planned_sets"]),
        item_type=TemplateItemType(str(item["item_type"])),
        display_name_snapshot=str(exercise["name"]),
        variation_group_snapshot=str(exercise["variation_group"]),
        rep_min_snapshot=item.get("rep_min"),
        rep_max_snapshot=item.get("rep_max"),
        duration_seconds_snapshot=item.get("duration_seconds"),
        distance_meters_snapshot=(
            Decimal(str(item["distance_meters"]))
            if item.get("distance_meters") is not None
            else None
        ),
        rounds_target_snapshot=item.get("rounds_target"),
        rest_seconds_snapshot=item.get("rest_seconds"),
        target_rir_snapshot=(
            Decimal(str(item["target_rir"])) if item.get("target_rir") is not None else None
        ),
        optional_snapshot=bool(item["optional"]),
        notes=item.get("notes"),
        substitution_reason=None,
        removed_at=None,
        removal_reason=None,
    )


def start_session(
    session: Session,
    user_id: str,
    write: StartSession,
    idempotency_key: str,
) -> WorkoutSession:
    operation = "session.start"
    receipt = replay_receipt(session, user_id, operation, idempotency_key, write)
    if receipt is not None:
        if receipt.result_resource_id is None:
            raise ApiError(409, "IDEMPOTENCY_CONFLICT", "The prior command has no session.")
        return require_session(session, user_id, receipt.result_resource_id)
    state = require_schedule(session, user_id)
    if state.version != write.expected_schedule_version:
        raise ApiError(409, "VERSION_CONFLICT", "The schedule changed. Refresh and try again.")
    profile = today_repository.profile(session, user_id)
    if profile is None:
        raise ApiError(503, "DATA_NOT_INITIALIZED", "Account data is unavailable.")
    local_date = write.date or datetime.now(UTC).astimezone(ZoneInfo(profile.timezone)).date()
    if today_repository.active_session(session, user_id, local_date) is not None:
        raise ApiError(
            409, "SESSION_ALREADY_STARTED", "An active session already exists for this date."
        )
    effective = resolve_effective_plan(session, user_id, local_date)
    split_day = effective.effective_day
    if write.split_day_id is not None:
        split_day = repository.split_day_by_id(session, user_id, write.split_day_id)
        if split_day is None:
            raise ApiError(404, "NOT_FOUND", "The selected split day was not found.")
        plan_items = exercise_plan_payload(
            type(effective)(local_date, split_day, split_day, None, None, []), user_id
        )
    else:
        plan_items = exercise_plan_payload(effective, user_id)
    workout = WorkoutSession(
        user_id=user_id,
        version=0,
        split_day_id=split_day.id if split_day else None,
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
        idempotency_key=None,
    )
    workout.exercises = [_snapshot_from_plan_item(workout, item) for item in plan_items]
    session.add(workout)
    try:
        session.flush()
        record_receipt(
            session,
            user_id,
            operation,
            idempotency_key,
            write,
            result_resource_id=workout.id,
            result_version=workout.version,
            status_code=201,
        )
    except IntegrityError as error:
        raise ApiError(
            409,
            "SESSION_ALREADY_STARTED",
            "An active session already exists for this date.",
        ) from error
    return workout


def update_session(
    session: Session, user_id: str, session_id: str, write: SessionUpdate
) -> WorkoutSession:
    workout = require_session(session, user_id, session_id)
    _require_mutable(workout)
    if write.status == "completed":
        raise ApiError(409, "IDEMPOTENCY_REQUIRED", "Use the session completion endpoint.")
    for field in ("title", "perceived_effort", "notes_private"):
        if field in write.model_fields_set:
            setattr(workout, field, getattr(write, field))
    if write.status is not None:
        workout.status = SessionStatus(write.status)
    workout.version += 1
    session.flush()
    return workout


def delete_session(session: Session, user_id: str, session_id: str) -> None:
    workout = require_session(session, user_id, session_id)
    _require_mutable(workout)
    workout.deleted_at = datetime.now(UTC)
    session.flush()
    for exercise_id in {item.exercise_id for item in workout.exercises}:
        rebuild_records(session, user_id, exercise_id)


def _require_session_exercise(
    session: Session, user_id: str, workout: WorkoutSession, item_id: str
) -> SessionExercise:
    item = repository.session_exercise_by_id(session, user_id, item_id)
    if item is None or item.workout_session_id != workout.id:
        raise ApiError(404, "NOT_FOUND", "The selected session exercise was not found.")
    return item


def add_or_substitute_exercise(
    session: Session, user_id: str, session_id: str, write: AddSessionExercise
) -> SessionExercise:
    workout = require_session(session, user_id, session_id)
    _require_mutable(workout)
    _version(workout, write.expected_version)
    exercise = repository.exercise_by_id(session, user_id, write.exercise_id)
    if exercise is None:
        raise ApiError(404, "NOT_FOUND", "The selected exercise was not found.")
    if write.replace_session_exercise_id is not None:
        item = _require_session_exercise(
            session, user_id, workout, write.replace_session_exercise_id
        )
        if item.removed_at is not None:
            raise ApiError(409, "EXERCISE_REMOVED", "A removed exercise cannot be substituted.")
        if any(row.deleted_at is None for row in item.sets):
            raise ApiError(
                409,
                "EXERCISE_HAS_SETS",
                "An exercise with logged sets cannot be relabeled.",
            )
        item.exercise = exercise
        item.display_name_snapshot = exercise.name
        item.variation_group_snapshot = exercise.variation_group
        item.rep_min_snapshot = exercise.default_rep_min
        item.rep_max_snapshot = exercise.default_rep_max
        item.rest_seconds_snapshot = exercise.default_rest_seconds
        item.substitution_reason = write.substitution_reason
    else:
        active = [item for item in workout.exercises if item.removed_at is None]
        sequence = write.sequence if write.sequence is not None else len(active)
        if sequence > len(active):
            raise ApiError(422, "VALIDATION_ERROR", "Exercise sequence is out of range.")
        for existing in active:
            if existing.sequence >= sequence:
                existing.sequence += 1000
        session.flush()
        for existing in active:
            if existing.sequence >= 1000:
                existing.sequence = existing.sequence - 999
        item = SessionExercise(
            workout_session=workout,
            exercise=exercise,
            source_template_item_id=None,
            sequence=sequence,
            planned_sets=1,
            item_type=TemplateItemType.ACCESSORY,
            display_name_snapshot=exercise.name,
            variation_group_snapshot=exercise.variation_group,
            rep_min_snapshot=exercise.default_rep_min,
            rep_max_snapshot=exercise.default_rep_max,
            duration_seconds_snapshot=None,
            distance_meters_snapshot=None,
            rounds_target_snapshot=None,
            rest_seconds_snapshot=exercise.default_rest_seconds,
            target_rir_snapshot=None,
            optional_snapshot=False,
            notes=None,
            substitution_reason=write.substitution_reason,
            removed_at=None,
            removal_reason=None,
        )
        session.add(item)
    workout.version += 1
    session.flush()
    return item


def update_session_exercise(
    session: Session,
    user_id: str,
    session_id: str,
    item_id: str,
    write: SessionExerciseUpdate,
) -> WorkoutSession:
    workout = require_session(session, user_id, session_id)
    _require_mutable(workout)
    _version(workout, write.expected_version)
    item = _require_session_exercise(session, user_id, workout, item_id)
    if item.removed_at is not None:
        raise ApiError(409, "EXERCISE_REMOVED", "A removed exercise cannot be changed.")
    if write.exercise_id is not None and write.exercise_id != item.exercise_id:
        if any(row.deleted_at is None for row in item.sets):
            raise ApiError(409, "EXERCISE_HAS_SETS", "Logged history cannot be relabeled.")
        exercise = repository.exercise_by_id(session, user_id, write.exercise_id)
        if exercise is None:
            raise ApiError(404, "NOT_FOUND", "The selected exercise was not found.")
        item.exercise = exercise
        item.display_name_snapshot = exercise.name
        item.variation_group_snapshot = exercise.variation_group
    mapping = {
        "planned_sets": "planned_sets",
        "item_type": "item_type",
        "rep_min": "rep_min_snapshot",
        "rep_max": "rep_max_snapshot",
        "duration_seconds": "duration_seconds_snapshot",
        "distance_meters": "distance_meters_snapshot",
        "rounds_target": "rounds_target_snapshot",
        "rest_seconds": "rest_seconds_snapshot",
        "target_rir": "target_rir_snapshot",
        "optional": "optional_snapshot",
        "notes": "notes",
        "substitution_reason": "substitution_reason",
    }
    for source, target in mapping.items():
        if source in write.model_fields_set:
            value = getattr(write, source)
            if source in {"distance_meters", "target_rir"} and value is not None:
                value = Decimal(str(value))
            setattr(item, target, value)
    workout.version += 1
    session.flush()
    return workout


def remove_session_exercise(
    session: Session,
    user_id: str,
    session_id: str,
    item_id: str,
    expected_version: int,
    *,
    confirm_logged_sets: bool,
) -> WorkoutSession:
    workout = require_session(session, user_id, session_id)
    _require_mutable(workout)
    _version(workout, expected_version)
    item = _require_session_exercise(session, user_id, workout, item_id)
    if item.removed_at is not None:
        raise ApiError(404, "NOT_FOUND", "The selected session exercise was not found.")
    if any(row.deleted_at is None for row in item.sets) and not confirm_logged_sets:
        raise ApiError(
            409,
            "CONFIRM_LOGGED_SETS",
            "Confirm removal to retain the logged sets in session history.",
        )
    item.removed_at = datetime.now(UTC)
    item.removal_reason = "Removed during active workout"
    item.sequence = max((row.sequence for row in workout.exercises), default=0) + 1000
    session.flush()
    active = sorted(
        (row for row in workout.exercises if row.removed_at is None), key=lambda row: row.sequence
    )
    for row in active:
        row.sequence += 2000
    session.flush()
    for sequence, row in enumerate(active):
        row.sequence = sequence
    workout.version += 1
    session.flush()
    return workout


def reorder_session_exercises(
    session: Session,
    user_id: str,
    session_id: str,
    write: ReorderSessionExercises,
) -> WorkoutSession:
    workout = require_session(session, user_id, session_id)
    _require_mutable(workout)
    _version(workout, write.expected_version)
    active = {item.id: item for item in workout.exercises if item.removed_at is None}
    if set(write.ordered_session_exercise_ids) != set(active):
        raise ApiError(422, "VALIDATION_ERROR", "The reorder list must contain every active item.")
    for item in active.values():
        item.sequence += 1000
    session.flush()
    for sequence, item_id in enumerate(write.ordered_session_exercise_ids):
        active[item_id].sequence = sequence
    workout.version += 1
    session.flush()
    return workout


def _validate_measurement(item: SessionExercise, write: SetWrite) -> None:
    measurement = item.exercise.measurement_type
    required = {
        MeasurementType.LOAD_REPS: (
            write.load_kg is not None and write.reps is not None,
            "load_kg and reps",
        ),
        MeasurementType.BODYWEIGHT_REPS: (write.reps is not None, "reps"),
        MeasurementType.DURATION: (write.duration_seconds is not None, "duration_seconds"),
        MeasurementType.DISTANCE: (write.distance_meters is not None, "distance_meters"),
        MeasurementType.ROUNDS: (write.rounds is not None, "rounds"),
    }[measurement]
    if not required[0]:
        raise ApiError(422, "VALIDATION_ERROR", f"{required[1]} is required for this exercise.")


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
    session: Session,
    user_id: str,
    session_id: str,
    write: SetWrite,
    idempotency_key: str | None,
) -> tuple[SetLog, RecordResult]:
    workout = require_session(session, user_id, session_id)
    _require_mutable(workout)
    scoped_key = (
        hashlib.sha256(f"{user_id}:{idempotency_key}".encode()).hexdigest()
        if idempotency_key
        else None
    )
    if idempotency_key:
        assert scoped_key is not None
        existing = repository.set_by_idempotency_key(session, user_id, scoped_key)
        if existing is not None:
            return existing, rebuild_records(
                session, user_id, existing.session_exercise.exercise_id
            )
    item = _require_session_exercise(session, user_id, workout, write.session_exercise_id)
    if item.removed_at is not None:
        raise ApiError(409, "EXERCISE_REMOVED", "Sets cannot be added to a removed exercise.")
    _validate_measurement(item, write)
    sequence = write.sequence or max((row.sequence for row in item.sets), default=0) + 1
    if any(row.sequence == sequence and row.deleted_at is None for row in item.sets):
        raise ApiError(422, "VALIDATION_ERROR", "That set sequence is already in use.")
    set_log = SetLog(
        session_exercise=item,
        sequence=sequence,
        completed_at=datetime.now(UTC),
        deleted_at=None,
        idempotency_key=scoped_key,
    )
    _apply_set_write(set_log, write)
    session.add(set_log)
    session.flush()
    return set_log, rebuild_records(session, user_id, item.exercise_id)


def update_set(
    session: Session, user_id: str, set_id: str, write: SetWrite
) -> tuple[SetLog, RecordResult]:
    set_log = repository.set_by_id(session, user_id, set_id)
    if set_log is None:
        raise ApiError(404, "NOT_FOUND", "The requested set was not found.")
    _require_mutable(set_log.session_exercise.workout_session)
    if write.session_exercise_id != set_log.session_exercise_id:
        raise ApiError(422, "VALIDATION_ERROR", "A set cannot be moved to another exercise.")
    _validate_measurement(set_log.session_exercise, write)
    if write.sequence is not None:
        if any(
            row.id != set_log.id and row.sequence == write.sequence and row.deleted_at is None
            for row in set_log.session_exercise.sets
        ):
            raise ApiError(422, "VALIDATION_ERROR", "That set sequence is already in use.")
        set_log.sequence = write.sequence
    _apply_set_write(set_log, write)
    session.flush()
    return set_log, rebuild_records(session, user_id, set_log.session_exercise.exercise_id)


def delete_set(session: Session, user_id: str, set_id: str) -> RecordResult:
    set_log = repository.set_by_id(session, user_id, set_id)
    if set_log is None:
        raise ApiError(404, "NOT_FOUND", "The requested set was not found.")
    _require_mutable(set_log.session_exercise.workout_session)
    set_log.deleted_at = datetime.now(UTC)
    session.flush()
    return rebuild_records(session, user_id, set_log.session_exercise.exercise_id)


def set_write_payload(set_log: SetLog, result: RecordResult) -> dict[str, object]:
    return {
        "set": serialize_admin_set(set_log),
        "new_achievements": serialize_public_achievements(result.new_achievements),
        "affected_records": [
            serialize_personal_record(record) for record in result.current_records
        ],
    }


def complete_session(
    session: Session, user_id: str, session_id: str, idempotency_key: str
) -> WorkoutSession:
    operation = "session.complete"
    payload = {"session_id": session_id}
    receipt = replay_receipt(session, user_id, operation, idempotency_key, payload)
    workout = require_session(session, user_id, session_id)
    if receipt is not None:
        return workout
    _require_mutable(workout)
    workout.status = SessionStatus.COMPLETED
    workout.completed_at = datetime.now(UTC)
    workout.version += 1
    session.flush()
    for exercise_id in {item.exercise_id for item in workout.exercises}:
        rebuild_records(session, user_id, exercise_id)
    state = require_schedule(session, user_id)
    if state.cursor_effective_date == workout.session_date_local:
        days = today_repository.split_days(session, user_id, state.active_split_id)
        if days and state.cursor_split_day_id:
            index = next(
                (i for i, item in enumerate(days) if item.id == state.cursor_split_day_id), None
            )
            if index is not None:
                weekdays = {
                    day.recommended_weekday for day in days if day.recommended_weekday is not None
                }
                next_date = workout.session_date_local + date.resolution
                while weekdays and next_date.weekday() not in weekdays:
                    next_date += date.resolution
                updated_state = today_repository.update_schedule(
                    session,
                    user_id,
                    state.version,
                    cursor_split_day_id=days[(index + 1) % len(days)].id,
                    cursor_effective_date=next_date,
                )
                if updated_state is None:
                    raise ApiError(
                        409,
                        "VERSION_CONFLICT",
                        "The schedule changed. Refresh and complete the workout again.",
                    )
                state = updated_state
    record_receipt(
        session,
        user_id,
        operation,
        idempotency_key,
        payload,
        result_resource_id=workout.id,
        result_version=state.version,
        status_code=200,
    )
    return workout
