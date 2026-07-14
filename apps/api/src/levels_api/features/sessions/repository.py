from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from levels_api.models import SplitDay, WorkoutSession


def all_sessions(session: Session) -> list[WorkoutSession]:
    return list(
        session.scalars(
            select(WorkoutSession)
            .where(WorkoutSession.deleted_at.is_(None))
            .order_by(WorkoutSession.session_date_local.desc(), WorkoutSession.started_at.desc())
        )
    )


def session_by_id(session: Session, session_id: str) -> WorkoutSession | None:
    return session.scalar(
        select(WorkoutSession).where(
            WorkoutSession.id == session_id, WorkoutSession.deleted_at.is_(None)
        )
    )


def session_by_idempotency_key(session: Session, key: str) -> WorkoutSession | None:
    return session.scalar(select(WorkoutSession).where(WorkoutSession.idempotency_key == key))


def split_day_by_id(session: Session, split_day_id: str) -> SplitDay | None:
    return session.get(SplitDay, split_day_id)
