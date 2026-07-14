from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from levels_api.models import Split


def all_splits(session: Session, *, include_archived: bool = False) -> list[Split]:
    statement = select(Split).order_by(Split.display_order, Split.name, Split.id)
    if not include_archived:
        statement = statement.where(Split.archived_at.is_(None))
    return list(session.scalars(statement))


def split_by_id(session: Session, split_id: str) -> Split | None:
    return session.scalar(select(Split).where(Split.id == split_id, Split.archived_at.is_(None)))


def split_by_slug(session: Session, slug: str) -> Split | None:
    return session.scalar(select(Split).where(Split.slug == slug))
