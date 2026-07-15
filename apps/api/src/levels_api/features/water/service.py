from __future__ import annotations

from datetime import UTC, date, datetime
from hashlib import sha256
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


def water_day(session: Session, user_id: str, local_date: date) -> dict[str, object]:
    profile = require_profile(session, user_id)
    assert profile.settings is not None
    return serialize_water_day(
        local_date,
        repository.entries_for_date(session, user_id, local_date),
        profile.settings.default_water_goal_ml,
    )


def add_water(
    session: Session, user_id: str, write: WaterWrite, idempotency_key: str | None
) -> dict[str, object]:
    profile = require_profile(session, user_id)
    stored_key: str | None = None
    if idempotency_key is not None:
        if not 1 <= len(idempotency_key) <= 128:
            raise ApiError(400, "VALIDATION_ERROR", "Idempotency-Key is invalid.")
        stored_key = sha256(f"{user_id}:{idempotency_key}".encode()).hexdigest()
        existing = repository.by_idempotency_key(session, user_id, stored_key)
        if existing is not None:
            return water_day(session, user_id, existing.local_date)
    occurred_at = (write.occurred_at or datetime.now(UTC)).astimezone(UTC)
    entry = WaterLog(
        user_id=user_id,
        occurred_at=occurred_at,
        local_date=local_date_for_profile(profile.timezone, occurred_at),
        amount_ml=write.amount_ml,
        source=WaterSource(write.source),
        note=write.note,
        idempotency_key=stored_key,
    )
    session.add(entry)
    session.flush()
    return water_day(session, user_id, entry.local_date)


def undo_latest(session: Session, user_id: str, local_date: date) -> dict[str, object]:
    entry = repository.latest_for_date(session, user_id, local_date)
    if entry is None:
        raise ApiError(404, "WATER_ENTRY_NOT_FOUND", "No water entry exists for this date.")
    session.delete(entry)
    session.flush()
    return water_day(session, user_id, local_date)
