from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from levels_api.models import Profile, Split


def get_profile(session: Session) -> Profile | None:
    return session.scalar(
        select(Profile)
        .options(selectinload(Profile.visibility), selectinload(Profile.settings))
        .limit(1)
    )


def split_exists(session: Session, split_id: str) -> bool:
    return session.scalar(select(Split.id).where(Split.id == split_id)) is not None
