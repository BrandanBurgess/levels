from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from levels_api.models import (
    Achievement,
    PersonalRecord,
    RecordType,
    SessionExercise,
    SessionStatus,
    SetLog,
    SetType,
    WorkoutSession,
)


@dataclass(frozen=True)
class Candidate:
    record_type: RecordType
    value: Decimal
    unit: str
    reps_context: int | None
    set_log: SetLog


@dataclass(frozen=True)
class RecordResult:
    new_achievements: list[Achievement]
    current_records: list[PersonalRecord]


def _eligible_sets(session: Session, exercise_id: str) -> list[SetLog]:
    return list(
        session.scalars(
            select(SetLog)
            .join(SetLog.session_exercise)
            .join(SessionExercise.workout_session)
            .where(
                SessionExercise.exercise_id == exercise_id,
                SetLog.deleted_at.is_(None),
                SetLog.set_type != SetType.WARMUP,
                WorkoutSession.deleted_at.is_(None),
                WorkoutSession.status != SessionStatus.CANCELLED,
            )
            .order_by(SetLog.completed_at, SetLog.id)
        )
    )


def _set_candidates(set_log: SetLog) -> list[Candidate]:
    result: list[Candidate] = []
    if set_log.load_kg is not None and set_log.reps is not None:
        result.extend(
            [
                Candidate(
                    RecordType.MAX_LOAD,
                    set_log.load_kg,
                    "kg",
                    set_log.reps,
                    set_log,
                ),
                Candidate(
                    RecordType.REPS_AT_LOAD,
                    Decimal(set_log.reps),
                    "reps",
                    set_log.reps,
                    set_log,
                ),
                Candidate(
                    RecordType.ESTIMATED_1RM,
                    set_log.load_kg * (Decimal(1) + Decimal(set_log.reps) / Decimal(30)),
                    "kg estimated",
                    set_log.reps,
                    set_log,
                ),
            ]
        )
    if set_log.duration_seconds is not None:
        result.append(
            Candidate(
                RecordType.DURATION,
                Decimal(set_log.duration_seconds),
                "seconds",
                None,
                set_log,
            )
        )
    if set_log.distance_meters is not None:
        result.append(
            Candidate(
                RecordType.DISTANCE,
                set_log.distance_meters,
                "meters",
                None,
                set_log,
            )
        )
    if set_log.rounds is not None:
        result.append(
            Candidate(
                RecordType.ROUNDS,
                Decimal(set_log.rounds),
                "rounds",
                None,
                set_log,
            )
        )
    return result


def _volume_candidates(sets: list[SetLog]) -> list[Candidate]:
    by_session: dict[str, list[SetLog]] = {}
    for set_log in sets:
        workout = set_log.session_exercise.workout_session
        if (
            workout.status == SessionStatus.COMPLETED
            and set_log.load_kg is not None
            and set_log.reps is not None
        ):
            by_session.setdefault(workout.id, []).append(set_log)
    result: list[Candidate] = []
    for session_sets in by_session.values():
        total = Decimal(0)
        for set_log in session_sets:
            assert set_log.load_kg is not None and set_log.reps is not None
            total += set_log.load_kg * set_log.reps
        source = max(session_sets, key=lambda item: (item.completed_at, item.id))
        result.append(Candidate(RecordType.SESSION_VOLUME, total, "kg reps", None, source))
    return result


def _achievement_copy(candidate: Candidate) -> tuple[str, str]:
    exercise_name = candidate.set_log.session_exercise.display_name_snapshot
    value = f"{candidate.value.quantize(Decimal('0.01')):f}".rstrip("0").rstrip(".")
    titles = {
        RecordType.MAX_LOAD: "New max load",
        RecordType.REPS_AT_LOAD: "New rep record",
        RecordType.ESTIMATED_1RM: "New estimated 1RM",
        RecordType.SESSION_VOLUME: "New session volume",
        RecordType.DURATION: "New duration record",
        RecordType.DISTANCE: "New distance record",
        RecordType.ROUNDS: "New rounds record",
    }
    if candidate.record_type == RecordType.ESTIMATED_1RM:
        message = (
            f"{exercise_name}: estimated 1RM {value} kg, calculated from a logged set. "
            "No max attempt is needed."
        )
    else:
        message = f"{exercise_name}: {value} {candidate.unit}."
    return titles[candidate.record_type], message


def _achievement_key(candidate: Candidate) -> str:
    return f"record:{candidate.set_log.id}:{candidate.record_type.value}"


def rebuild_records(session: Session, exercise_id: str) -> RecordResult:
    sets = _eligible_sets(session, exercise_id)
    candidates = [candidate for set_log in sets for candidate in _set_candidates(set_log)]
    candidates.extend(_volume_candidates(sets))
    candidates.sort(
        key=lambda candidate: (
            candidate.set_log.completed_at.replace(
                tzinfo=candidate.set_log.completed_at.tzinfo or UTC
            ).timestamp(),
            candidate.set_log.id,
            candidate.record_type.value,
        )
    )

    existing_records = list(
        session.scalars(select(PersonalRecord).where(PersonalRecord.exercise_id == exercise_id))
    )
    for record in existing_records:
        session.delete(record)
    session.flush()

    best: dict[RecordType, Decimal] = {}
    expected_achievements: dict[str, Candidate] = {}
    records: list[PersonalRecord] = []
    for candidate in candidates:
        if candidate.value <= best.get(candidate.record_type, Decimal("-1")):
            continue
        for record in records:
            if record.record_type == candidate.record_type:
                record.is_current = False
        record = PersonalRecord(
            exercise_id=exercise_id,
            record_type=candidate.record_type,
            value_numeric=candidate.value.quantize(Decimal("0.0001")),
            unit=candidate.unit,
            reps_context=candidate.reps_context,
            set_log=candidate.set_log,
            achieved_at=candidate.set_log.completed_at,
            is_current=True,
        )
        session.add(record)
        records.append(record)
        best[candidate.record_type] = candidate.value
        expected_achievements[_achievement_key(candidate)] = candidate

    existing_achievements = {
        achievement.idempotency_key: achievement
        for achievement in session.scalars(
            select(Achievement).where(
                Achievement.exercise_id == exercise_id,
                Achievement.achievement_type == "personal_record",
            )
        )
    }
    new_achievements: list[Achievement] = []
    for key, candidate in expected_achievements.items():
        title, message = _achievement_copy(candidate)
        achievement = existing_achievements.pop(key, None)
        if achievement is None:
            achievement = Achievement(
                achievement_type="personal_record",
                exercise_id=exercise_id,
                set_log=candidate.set_log,
                title=title,
                message=message,
                achieved_at=candidate.set_log.completed_at,
                public=True,
                idempotency_key=key,
            )
            session.add(achievement)
            new_achievements.append(achievement)
        else:
            achievement.set_log = candidate.set_log
            achievement.title = title
            achievement.message = message
            achievement.achieved_at = candidate.set_log.completed_at
    for stale in existing_achievements.values():
        session.delete(stale)
    session.flush()
    return RecordResult(
        new_achievements=new_achievements,
        current_records=[record for record in records if record.is_current],
    )
