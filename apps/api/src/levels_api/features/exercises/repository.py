from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from levels_api.models import Exercise, ExerciseMuscle, MuscleGroup


def all_exercises(session: Session, user_id: str, scope: str) -> list[Exercise]:
    statement = (
        select(Exercise)
        .options(selectinload(Exercise.muscle_links).selectinload(ExerciseMuscle.muscle_group))
        .order_by(Exercise.name, Exercise.id)
    )
    if scope == "global":
        statement = statement.where(Exercise.owner_user_id.is_(None))
    elif scope == "mine":
        statement = statement.where(Exercise.owner_user_id == user_id)
    else:
        statement = statement.where(
            (Exercise.owner_user_id.is_(None)) | (Exercise.owner_user_id == user_id)
        )
    return list(session.scalars(statement).unique())


def exercise_by_id(session: Session, user_id: str, exercise_id: str) -> Exercise | None:
    statement = (
        select(Exercise)
        .where(
            Exercise.id == exercise_id,
            (Exercise.owner_user_id.is_(None)) | (Exercise.owner_user_id == user_id),
        )
        .options(selectinload(Exercise.muscle_links).selectinload(ExerciseMuscle.muscle_group))
    )
    return session.scalar(statement)


def exercise_by_slug(session: Session, user_id: str, slug: str) -> Exercise | None:
    return session.scalar(
        select(Exercise).where(Exercise.owner_user_id == user_id, Exercise.slug == slug)
    )


def all_muscle_groups(session: Session) -> list[MuscleGroup]:
    return list(session.scalars(select(MuscleGroup).order_by(MuscleGroup.display_name)))
