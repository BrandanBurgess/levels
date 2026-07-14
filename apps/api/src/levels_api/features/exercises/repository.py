from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from levels_api.models import Exercise, ExerciseMuscle


def all_exercises(session: Session) -> list[Exercise]:
    statement = (
        select(Exercise)
        .options(selectinload(Exercise.muscle_links).selectinload(ExerciseMuscle.muscle_group))
        .order_by(Exercise.name, Exercise.id)
    )
    return list(session.scalars(statement).unique())


def exercise_by_id(session: Session, exercise_id: str) -> Exercise | None:
    statement = (
        select(Exercise)
        .where(Exercise.id == exercise_id)
        .options(selectinload(Exercise.muscle_links).selectinload(ExerciseMuscle.muscle_group))
    )
    return session.scalar(statement)


def exercise_by_slug(session: Session, slug: str) -> Exercise | None:
    return session.scalar(select(Exercise).where(Exercise.slug == slug))
