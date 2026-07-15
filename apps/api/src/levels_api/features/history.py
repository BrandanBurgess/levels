from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from levels_api.models import Split, SplitDay, WorkoutTemplateItem

HISTORY_SPLIT_SLUG = "__levels_history__"
HISTORY_ITEMS_DAY_TYPE = "history_archive"


def _archive_split(session: Session, user_id: str) -> Split:
    split = session.scalar(
        select(Split).where(Split.user_id == user_id, Split.slug == HISTORY_SPLIT_SLUG)
    )
    if split is None:
        split = Split(
            user_id=user_id,
            name="Retired training history",
            slug=HISTORY_SPLIT_SLUG,
            description="Internal archive preserving completed workout references.",
            is_active=False,
            is_seeded=False,
            display_order=2_147_483_647,
            archived_at=datetime.now(UTC),
        )
        session.add(split)
        session.flush()
    return split


def _archive_item_day(session: Session, user_id: str) -> SplitDay:
    split = _archive_split(session, user_id)
    day = session.scalar(
        select(SplitDay).where(
            SplitDay.split_id == split.id,
            SplitDay.day_type == HISTORY_ITEMS_DAY_TYPE,
        )
    )
    if day is None:
        next_sequence = session.scalar(
            select(func.coalesce(func.max(SplitDay.sequence), 0)).where(
                SplitDay.split_id == split.id
            )
        )
        day = SplitDay(
            split_id=split.id,
            name="Retired template items",
            day_type=HISTORY_ITEMS_DAY_TYPE,
            sequence=int(next_sequence or 0) + 1,
            recommended_weekday=None,
            description="Internal history archive.",
            is_optional=True,
        )
        session.add(day)
        session.flush()
    return day


def archive_template_item(session: Session, user_id: str, item: WorkoutTemplateItem) -> None:
    day = _archive_item_day(session, user_id)
    next_sequence = session.scalar(
        select(func.coalesce(func.max(WorkoutTemplateItem.sequence), 0)).where(
            WorkoutTemplateItem.split_day_id == day.id
        )
    )
    item.split_day = day
    item.sequence = int(next_sequence or 0) + 1
    session.flush()


def archive_split_day(session: Session, user_id: str, day: SplitDay) -> None:
    split = _archive_split(session, user_id)
    next_sequence = session.scalar(
        select(func.coalesce(func.max(SplitDay.sequence), 0)).where(SplitDay.split_id == split.id)
    )
    day.split = split
    day.sequence = int(next_sequence or 0) + 1
    day.recommended_weekday = None
    session.flush()
