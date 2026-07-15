from __future__ import annotations

from datetime import date
from typing import Any, cast

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session, selectinload

from levels_api.models import (
    Achievement,
    AvatarSettings,
    CommandReceipt,
    DailyExercisePlan,
    DailyExercisePlanItem,
    DailyPlanOverride,
    Exercise,
    ExerciseMuscle,
    Profile,
    ScheduleState,
    SessionExercise,
    Split,
    SplitDay,
    TemplateAlternative,
    User,
    WaterLog,
    WorkoutSession,
    WorkoutTemplateItem,
)


def _day_options() -> tuple[Any, ...]:
    return (
        selectinload(SplitDay.items)
        .selectinload(WorkoutTemplateItem.exercise)
        .selectinload(Exercise.muscle_links),
        selectinload(SplitDay.items)
        .selectinload(WorkoutTemplateItem.exercise)
        .selectinload(Exercise.muscle_links)
        .selectinload(ExerciseMuscle.muscle_group),
        selectinload(SplitDay.items)
        .selectinload(WorkoutTemplateItem.alternatives)
        .selectinload(TemplateAlternative.exercise),
    )


def user(session: Session, user_id: str) -> User | None:
    return session.get(User, user_id)


def profile(session: Session, user_id: str) -> Profile | None:
    return session.scalar(
        select(Profile)
        .where(Profile.user_id == user_id)
        .options(selectinload(Profile.settings), selectinload(Profile.visibility))
    )


def schedule_state(session: Session, user_id: str) -> ScheduleState | None:
    return session.get(ScheduleState, user_id)


def update_schedule(
    session: Session,
    user_id: str,
    expected_version: int,
    **values: object,
) -> ScheduleState | None:
    values["version"] = expected_version + 1
    result = session.execute(
        update(ScheduleState)
        .where(ScheduleState.user_id == user_id, ScheduleState.version == expected_version)
        .values(**values)
    )
    if cast(Any, result).rowcount != 1:
        return None
    state = session.get(ScheduleState, user_id)
    assert state is not None
    session.refresh(state)
    return state


def split_days(session: Session, user_id: str, split_id: str | None) -> list[SplitDay]:
    if split_id is None:
        return []
    return list(
        session.scalars(
            select(SplitDay)
            .join(SplitDay.split)
            .where(Split.id == split_id, Split.user_id == user_id, Split.archived_at.is_(None))
            .options(*_day_options())
            .order_by(SplitDay.sequence)
        )
    )


def scheduled_day(
    session: Session,
    user_id: str,
    split_id: str | None,
    weekday: int,
) -> SplitDay | None:
    if split_id is None:
        return None
    return session.scalar(
        select(SplitDay)
        .join(SplitDay.split)
        .where(
            Split.id == split_id,
            Split.user_id == user_id,
            Split.archived_at.is_(None),
            SplitDay.recommended_weekday == weekday,
        )
        .options(*_day_options())
    )


def split_day(session: Session, user_id: str, split_day_id: str) -> SplitDay | None:
    return session.scalar(
        select(SplitDay)
        .join(SplitDay.split)
        .where(
            SplitDay.id == split_day_id,
            Split.user_id == user_id,
            Split.archived_at.is_(None),
        )
        .options(*_day_options())
    )


def override_for_date(session: Session, user_id: str, local_date: date) -> DailyPlanOverride | None:
    return session.scalar(
        select(DailyPlanOverride).where(
            DailyPlanOverride.user_id == user_id,
            DailyPlanOverride.local_date == local_date,
        )
    )


def overrides_for_group(
    session: Session, user_id: str, swap_group_id: str
) -> list[DailyPlanOverride]:
    return list(
        session.scalars(
            select(DailyPlanOverride).where(
                DailyPlanOverride.user_id == user_id,
                DailyPlanOverride.swap_group_id == swap_group_id,
            )
        )
    )


def exercise_plan(session: Session, user_id: str, local_date: date) -> DailyExercisePlan | None:
    return session.scalar(
        select(DailyExercisePlan).where(
            DailyExercisePlan.user_id == user_id,
            DailyExercisePlan.local_date == local_date,
        )
    )


def exercise_plan_items(
    session: Session, plan_id: str
) -> list[tuple[DailyExercisePlanItem, Exercise]]:
    return list(
        session.execute(
            select(DailyExercisePlanItem, Exercise)
            .join(Exercise, Exercise.id == DailyExercisePlanItem.exercise_id)
            .where(DailyExercisePlanItem.daily_exercise_plan_id == plan_id)
            .options(selectinload(Exercise.muscle_links).selectinload(ExerciseMuscle.muscle_group))
            .order_by(DailyExercisePlanItem.sequence)
        ).tuples()
    )


def active_session(session: Session, user_id: str, local_date: date) -> WorkoutSession | None:
    return session.scalar(
        select(WorkoutSession)
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.session_date_local == local_date,
            WorkoutSession.status.in_(("draft", "in_progress")),
            WorkoutSession.deleted_at.is_(None),
        )
        .options(selectinload(WorkoutSession.exercises).selectinload(SessionExercise.sets))
        .order_by(WorkoutSession.started_at.desc())
        .limit(1)
    )


def latest_achievements(session: Session, user_id: str, limit: int = 5) -> list[Achievement]:
    return list(
        session.scalars(
            select(Achievement)
            .where(Achievement.user_id == user_id)
            .order_by(Achievement.achieved_at.desc())
            .limit(limit)
        )
    )


def avatar(session: Session, user_id: str) -> AvatarSettings | None:
    return session.get(AvatarSettings, user_id)


def water_entries(session: Session, user_id: str, local_date: date) -> list[WaterLog]:
    return list(
        session.scalars(
            select(WaterLog)
            .where(WaterLog.user_id == user_id, WaterLog.local_date == local_date)
            .order_by(WaterLog.occurred_at, WaterLog.created_at, WaterLog.id)
        )
    )


def available_exercise(session: Session, user_id: str, exercise_id: str) -> Exercise | None:
    return session.scalar(
        select(Exercise)
        .where(
            Exercise.id == exercise_id,
            Exercise.archived_at.is_(None),
            or_(Exercise.owner_user_id.is_(None), Exercise.owner_user_id == user_id),
        )
        .options(selectinload(Exercise.muscle_links).selectinload(ExerciseMuscle.muscle_group))
    )


def command_receipt(
    session: Session, user_id: str, operation: str, key: str
) -> CommandReceipt | None:
    return session.scalar(
        select(CommandReceipt).where(
            CommandReceipt.user_id == user_id,
            CommandReceipt.operation == operation,
            CommandReceipt.idempotency_key == key,
        )
    )
