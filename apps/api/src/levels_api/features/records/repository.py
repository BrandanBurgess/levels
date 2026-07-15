from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from levels_api.models import (
    PersonalRecord,
)


def records(
    session: Session,
    user_id: str,
    *,
    exercise_id: str | None,
    current_only: bool,
) -> list[PersonalRecord]:
    statement = (
        select(PersonalRecord)
        .where(PersonalRecord.user_id == user_id)
        .options(selectinload(PersonalRecord.exercise))
    )
    if exercise_id is not None:
        statement = statement.where(PersonalRecord.exercise_id == exercise_id)
    if current_only:
        statement = statement.where(PersonalRecord.is_current.is_(True))
    statement = statement.order_by(PersonalRecord.achieved_at.desc(), PersonalRecord.id)
    return list(session.scalars(statement).unique())
