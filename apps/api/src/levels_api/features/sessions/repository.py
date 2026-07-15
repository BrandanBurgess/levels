from __future__ import annotations

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from levels_api.models import (
    Exercise,
    SessionExercise,
    SetLog,
    Split,
    SplitDay,
    WorkoutSession,
    WorkoutTemplateItem,
)


def all_sessions(
    session: Session,
    user_id: str,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    exercise_id: str | None = None,
) -> list[WorkoutSession]:
    query = select(WorkoutSession).where(
        WorkoutSession.user_id == user_id, WorkoutSession.deleted_at.is_(None)
    )
    if date_from is not None:
        query = query.where(WorkoutSession.session_date_local >= date_from)
    if date_to is not None:
        query = query.where(WorkoutSession.session_date_local <= date_to)
    if exercise_id is not None:
        query = query.where(
            WorkoutSession.exercises.any(SessionExercise.exercise_id == exercise_id)
        )
    return list(
        session.scalars(
            query.options(
                selectinload(WorkoutSession.exercises).selectinload(SessionExercise.sets)
            ).order_by(WorkoutSession.session_date_local.desc(), WorkoutSession.started_at.desc())
        )
    )


def session_by_id(session: Session, user_id: str, session_id: str) -> WorkoutSession | None:
    return session.scalar(
        select(WorkoutSession)
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.id == session_id,
            WorkoutSession.deleted_at.is_(None),
        )
        .options(selectinload(WorkoutSession.exercises).selectinload(SessionExercise.sets))
    )


def split_day_by_id(session: Session, user_id: str, split_day_id: str) -> SplitDay | None:
    return session.scalar(
        select(SplitDay)
        .join(SplitDay.split)
        .where(SplitDay.id == split_day_id, Split.user_id == user_id)
        .options(
            selectinload(SplitDay.items).selectinload(WorkoutTemplateItem.exercise),
        )
    )


def exercise_by_id(session: Session, user_id: str, exercise_id: str) -> Exercise | None:
    return session.scalar(
        select(Exercise).where(
            Exercise.id == exercise_id,
            Exercise.archived_at.is_(None),
            or_(Exercise.owner_user_id.is_(None), Exercise.owner_user_id == user_id),
        )
    )


def session_exercise_by_id(session: Session, user_id: str, item_id: str) -> SessionExercise | None:
    return session.scalar(
        select(SessionExercise)
        .join(SessionExercise.workout_session)
        .where(SessionExercise.id == item_id, WorkoutSession.user_id == user_id)
        .options(selectinload(SessionExercise.sets))
    )


def set_by_id(session: Session, user_id: str, set_id: str) -> SetLog | None:
    return session.scalar(
        select(SetLog)
        .join(SetLog.session_exercise)
        .join(SessionExercise.workout_session)
        .where(
            SetLog.id == set_id,
            SetLog.deleted_at.is_(None),
            WorkoutSession.user_id == user_id,
        )
    )


def set_by_idempotency_key(session: Session, user_id: str, key: str) -> SetLog | None:
    return session.scalar(
        select(SetLog)
        .join(SetLog.session_exercise)
        .join(SessionExercise.workout_session)
        .where(SetLog.idempotency_key == key, WorkoutSession.user_id == user_id)
    )
