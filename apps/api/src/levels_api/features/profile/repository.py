from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from levels_api.models import Profile, Split


def get_profile(session: Session, user_id: str) -> Profile | None:
    return session.scalar(
        select(Profile)
        .where(Profile.user_id == user_id)
        .options(selectinload(Profile.visibility), selectinload(Profile.settings))
    )


def split_exists(session: Session, user_id: str, split_id: str) -> bool:
    return (
        session.scalar(select(Split.id).where(Split.id == split_id, Split.user_id == user_id))
        is not None
    )
