from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from levels_api.models import (
    PersonalRecord,
    PublicVisibility,
    SessionExercise,
    SessionStatus,
    SetLog,
    WorkoutSession,
)


def records(
    session: Session,
    *,
    exercise_id: str | None,
    current_only: bool,
    owner: bool,
) -> list[PersonalRecord]:
    statement = select(PersonalRecord).options(selectinload(PersonalRecord.exercise))
    if exercise_id is not None:
        statement = statement.where(PersonalRecord.exercise_id == exercise_id)
    if current_only:
        statement = statement.where(PersonalRecord.is_current.is_(True))
    if not owner:
        statement = (
            statement.join(PersonalRecord.set_log)
            .join(SetLog.session_exercise)
            .join(SessionExercise.workout_session)
            .where(
                WorkoutSession.status == SessionStatus.COMPLETED,
                WorkoutSession.deleted_at.is_(None),
                WorkoutSession.public_visibility != PublicVisibility.PRIVATE,
                SetLog.deleted_at.is_(None),
            )
        )
    statement = statement.order_by(PersonalRecord.achieved_at.desc(), PersonalRecord.id)
    return list(session.scalars(statement).unique())
