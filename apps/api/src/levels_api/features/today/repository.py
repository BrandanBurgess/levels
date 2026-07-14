from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from levels_api.models import (
    Achievement,
    Exercise,
    SessionExercise,
    SplitDay,
    TemplateAlternative,
    WorkoutSession,
    WorkoutTemplateItem,
)


def scheduled_day(session: Session, split_id: str | None, weekday: int) -> SplitDay | None:
    if split_id is None:
        return None
    return session.scalar(
        select(SplitDay)
        .where(
            SplitDay.split_id == split_id,
            SplitDay.recommended_weekday == weekday,
        )
        .options(
            selectinload(SplitDay.items)
            .selectinload(WorkoutTemplateItem.exercise)
            .selectinload(Exercise.muscle_links),
            selectinload(SplitDay.items)
            .selectinload(WorkoutTemplateItem.alternatives)
            .selectinload(TemplateAlternative.exercise),
        )
    )


def active_session(session: Session, local_date: date) -> WorkoutSession | None:
    return session.scalar(
        select(WorkoutSession)
        .where(
            WorkoutSession.session_date_local == local_date,
            WorkoutSession.status.in_(("draft", "in_progress")),
            WorkoutSession.deleted_at.is_(None),
        )
        .options(selectinload(WorkoutSession.exercises).selectinload(SessionExercise.sets))
        .order_by(WorkoutSession.started_at.desc())
        .limit(1)
    )


def latest_achievements(session: Session, limit: int = 5) -> list[Achievement]:
    return list(
        session.scalars(
            select(Achievement)
            .where(Achievement.public.is_(True))
            .order_by(Achievement.achieved_at.desc())
            .limit(limit)
        )
    )
