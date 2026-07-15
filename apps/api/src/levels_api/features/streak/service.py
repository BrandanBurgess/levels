from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from levels_api.models import DailyPlanOverride, OverrideAction, SessionStatus, WorkoutSession

MILESTONES = (3, 7, 14, 30)


def _tier(count: int) -> str:
    if count >= 30:
        return "legendary"
    if count >= 14:
        return "energized"
    if count >= 7:
        return "active"
    if count >= 3:
        return "subtle"
    return "none"


def _next_milestone(count: int) -> int | None:
    return next((milestone for milestone in MILESTONES if milestone > count), None)


def streak_summary(
    session: Session, user_id: str, *, through_date: date | None = None
) -> dict[str, int | str | None]:
    cutoff = through_date or date.today()
    completed_dates = set(
        session.scalars(
            select(WorkoutSession.session_date_local).where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.status == SessionStatus.COMPLETED,
                WorkoutSession.deleted_at.is_(None),
                WorkoutSession.session_date_local <= cutoff,
            )
        )
    )
    skipped_dates = set(
        session.scalars(
            select(DailyPlanOverride.local_date).where(
                DailyPlanOverride.user_id == user_id,
                DailyPlanOverride.action == OverrideAction.SKIP,
                DailyPlanOverride.local_date <= cutoff,
            )
        )
    )

    current = 0
    longest = 0
    for local_date in sorted(completed_dates | skipped_dates):
        if local_date in skipped_dates:
            current = 0
        elif local_date in completed_dates:
            current += 1
            longest = max(longest, current)

    return {
        "current_count": current,
        "longest_count": longest,
        "tier": _tier(current),
        "last_qualified_local_date": (
            max(completed_dates).isoformat() if completed_dates else None
        ),
        "next_milestone": _next_milestone(current),
    }
