from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from levels_api.models import WaterLog


def entries_for_date(session: Session, local_date: date) -> list[WaterLog]:
    return list(
        session.scalars(
            select(WaterLog)
            .where(WaterLog.local_date == local_date)
            .order_by(WaterLog.occurred_at, WaterLog.created_at, WaterLog.id)
        )
    )


def latest_for_date(session: Session, local_date: date) -> WaterLog | None:
    return session.scalar(
        select(WaterLog)
        .where(WaterLog.local_date == local_date)
        .order_by(WaterLog.occurred_at.desc(), WaterLog.created_at.desc(), WaterLog.id.desc())
        .limit(1)
    )


def by_idempotency_key(session: Session, key: str) -> WaterLog | None:
    return session.scalar(select(WaterLog).where(WaterLog.idempotency_key == key))
