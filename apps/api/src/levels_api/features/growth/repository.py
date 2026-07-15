from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from levels_api.models import (
    ReadinessLog,
    SessionExercise,
    SessionStatus,
    SetLog,
    SetType,
    WorkoutSession,
)


def recent_exercise_sessions(
    session: Session, user_id: str, exercise_id: str, *, limit: int = 3
) -> list[SessionExercise]:
    statement = (
        select(SessionExercise)
        .join(SessionExercise.workout_session)
        .join(SessionExercise.sets)
        .where(
            SessionExercise.exercise_id == exercise_id,
            WorkoutSession.user_id == user_id,
            WorkoutSession.status == SessionStatus.COMPLETED,
            WorkoutSession.deleted_at.is_(None),
            SetLog.deleted_at.is_(None),
            SetLog.set_type != SetType.WARMUP,
        )
        .options(selectinload(SessionExercise.sets))
        .order_by(
            WorkoutSession.session_date_local.desc(),
            WorkoutSession.completed_at.desc(),
        )
        .distinct()
        .limit(limit)
    )
    return list(session.scalars(statement).unique())


def readiness_on(session: Session, user_id: str, local_date: date) -> ReadinessLog | None:
    return session.scalar(
        select(ReadinessLog).where(
            ReadinessLog.user_id == user_id,
            ReadinessLog.local_date == local_date,
        )
    )


def active_sets(item: SessionExercise) -> list[SetLog]:
    return [
        set_log
        for set_log in item.sets
        if set_log.deleted_at is None and set_log.set_type.value != "warmup"
    ]
