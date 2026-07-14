from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from levels_api.errors import ApiError
from levels_api.features.profile.service import require_profile
from levels_api.models import WaterLog, WaterSource
from levels_api.schemas import serialize_water_day

from . import repository
from .schemas import WaterWrite


def local_date_for_profile(timezone: str, occurred_at: datetime | None = None) -> date:
    instant = occurred_at or datetime.now(UTC)
    return instant.astimezone(ZoneInfo(timezone)).date()


def water_day(session: Session, local_date: date) -> dict[str, object]:
    profile = require_profile(session)
    assert profile.settings is not None
    return serialize_water_day(
        local_date,
        repository.entries_for_date(session, local_date),
        profile.settings.default_water_goal_ml,
    )


def add_water(
    session: Session, write: WaterWrite, idempotency_key: str | None
) -> dict[str, object]:
    profile = require_profile(session)
    if idempotency_key is not None:
        if not 1 <= len(idempotency_key) <= 128:
            raise ApiError(400, "VALIDATION_ERROR", "Idempotency-Key is invalid.")
        existing = repository.by_idempotency_key(session, idempotency_key)
        if existing is not None:
            return water_day(session, existing.local_date)
    occurred_at = (write.occurred_at or datetime.now(UTC)).astimezone(UTC)
    entry = WaterLog(
        occurred_at=occurred_at,
        local_date=local_date_for_profile(profile.timezone, occurred_at),
        amount_ml=write.amount_ml,
        source=WaterSource(write.source),
        note=write.note,
        idempotency_key=idempotency_key,
    )
    session.add(entry)
    session.flush()
    return water_day(session, entry.local_date)


def undo_latest(session: Session, local_date: date) -> dict[str, object]:
    entry = repository.latest_for_date(session, local_date)
    if entry is None:
        raise ApiError(404, "WATER_ENTRY_NOT_FOUND", "No water entry exists for this date.")
    session.delete(entry)
    session.flush()
    return water_day(session, local_date)
