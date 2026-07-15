from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from levels_api.features.streak.service import streak_summary
from levels_api.models import (
    Base,
    DailyPlanOverride,
    OverrideAction,
    ScheduleEffect,
    SessionStatus,
    User,
    UserRole,
    UserStatus,
    WorkoutSession,
)


def _user(user_id: str) -> User:
    return User(
        id=user_id,
        email_normalized=f"{user_id}@example.com",
        password_hash="$argon2id$fixture",
        status=UserStatus.ACTIVE,
        role=UserRole.MEMBER,
        token_version=0,
        is_demo=False,
    )


def _completed(user_id: str, local_date: date) -> WorkoutSession:
    return WorkoutSession(
        user_id=user_id,
        version=0,
        session_date_local=local_date,
        started_at=datetime.combine(local_date, datetime.min.time(), tzinfo=UTC),
        completed_at=datetime.combine(local_date, datetime.min.time(), tzinfo=UTC),
        status=SessionStatus.COMPLETED,
        title=f"Workout {local_date}",
    )


def test_streak_counts_opportunities_ignores_rest_and_reschedule_and_scopes_tenant() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    start = date(2026, 1, 1)
    with Session(engine) as session, session.begin():
        session.add_all([_user("user-a"), _user("user-b")])
        session.add_all(
            _completed("user-a", start + timedelta(days=index * 2)) for index in range(8)
        )
        session.add_all(
            [
                DailyPlanOverride(
                    user_id="user-a",
                    local_date=start + timedelta(days=3),
                    action=OverrideAction.REST,
                    schedule_effect=ScheduleEffect.ONE_TIME,
                    version=0,
                ),
                DailyPlanOverride(
                    user_id="user-a",
                    local_date=start + timedelta(days=5),
                    action=OverrideAction.REPLACE,
                    schedule_effect=ScheduleEffect.CONTINUE_FROM_HERE,
                    version=0,
                ),
                DailyPlanOverride(
                    user_id="user-a",
                    local_date=start + timedelta(days=17),
                    action=OverrideAction.SKIP,
                    schedule_effect=ScheduleEffect.ADVANCE,
                    version=0,
                ),
            ]
        )
        session.add_all(
            _completed("user-a", start + timedelta(days=18 + index * 2)) for index in range(3)
        )
        session.add_all(_completed("user-b", start + timedelta(days=index)) for index in range(30))

    with Session(engine) as session:
        summary_a = streak_summary(session, "user-a", through_date=date(2026, 3, 1))
        summary_b = streak_summary(session, "user-b", through_date=date(2026, 3, 1))

    assert summary_a == {
        "current_count": 3,
        "longest_count": 8,
        "tier": "subtle",
        "last_qualified_local_date": "2026-01-23",
        "next_milestone": 7,
    }
    assert summary_b["current_count"] == 30
    assert summary_b["tier"] == "legendary"
    assert summary_b["next_milestone"] is None
    engine.dispose()
