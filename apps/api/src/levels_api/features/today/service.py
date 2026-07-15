from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import cast
from uuid import uuid4

from sqlalchemy import delete
from sqlalchemy.orm import Session

from levels_api.auth.service import current_user_payload
from levels_api.errors import ApiError
from levels_api.features.exercises.service import serialize_exercise
from levels_api.features.history import archive_template_item
from levels_api.features.streak.service import streak_summary
from levels_api.models import (
    AvatarSettings,
    CommandReceipt,
    DailyExercisePlan,
    DailyExercisePlanItem,
    DailyPlanOverride,
    Exercise,
    MuscleRole,
    OverrideAction,
    ScheduleEffect,
    ScheduleState,
    SplitDay,
    WorkoutTemplateItem,
)
from levels_api.schemas import serialize_public_achievements, serialize_water_day

from . import repository
from .schemas import SkipTodayRequest, TodayExercisePlanUpdate, TodayOverrideRequest


@dataclass(frozen=True, slots=True)
class EffectivePlan:
    local_date: date
    planned_day: SplitDay | None
    effective_day: SplitDay | None
    override: DailyPlanOverride | None
    daily_plan: DailyExercisePlan | None
    daily_items: list[tuple[DailyExercisePlanItem, Exercise]]


def _conflict(message: str = "The schedule changed. Refresh and try again.") -> ApiError:
    return ApiError(409, "VERSION_CONFLICT", message)


def _request_hash(payload: object) -> str:
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json", exclude_none=False)  # type: ignore[union-attr]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()


def replay_receipt(
    session: Session,
    user_id: str,
    operation: str,
    key: str,
    payload: object,
) -> CommandReceipt | None:
    receipt = repository.command_receipt(session, user_id, operation, key)
    if receipt is not None and receipt.request_hash != _request_hash(payload):
        raise ApiError(
            409,
            "IDEMPOTENCY_CONFLICT",
            "That idempotency key was already used for a different request.",
        )
    return receipt


def record_receipt(
    session: Session,
    user_id: str,
    operation: str,
    key: str,
    payload: object,
    *,
    result_resource_id: str | None,
    result_version: int | None,
    status_code: int,
) -> CommandReceipt:
    receipt = CommandReceipt(
        user_id=user_id,
        operation=operation,
        idempotency_key=key,
        request_hash=_request_hash(payload),
        result_resource_id=result_resource_id,
        result_version=result_version,
        status_code=status_code,
    )
    session.add(receipt)
    session.flush()
    return receipt


def require_schedule(session: Session, user_id: str) -> ScheduleState:
    state = repository.schedule_state(session, user_id)
    if state is None:
        raise ApiError(503, "DATA_NOT_INITIALIZED", "Schedule data is unavailable.")
    return state


def _ordered_days(session: Session, user_id: str, split_id: str | None) -> list[SplitDay]:
    return repository.split_days(session, user_id, split_id)


def _next_opportunity(after: date, days: list[SplitDay]) -> date:
    weekdays = {day.recommended_weekday for day in days if day.recommended_weekday is not None}
    if not weekdays:
        return after + timedelta(days=1)
    candidate = after + timedelta(days=1)
    for _ in range(14):
        if candidate.weekday() in weekdays:
            return candidate
        candidate += timedelta(days=1)
    raise ApiError(500, "INVALID_SCHEDULE", "The active split has no planning opportunity.")


def _next_day(days: list[SplitDay], current: SplitDay) -> SplitDay:
    index = next((i for i, item in enumerate(days) if item.id == current.id), None)
    if index is None:
        raise ApiError(409, "SCHEDULE_MISMATCH", "The selected day is outside the active split.")
    return days[(index + 1) % len(days)]


def _cursor_planned_day(
    session: Session, user_id: str, local_date: date, state: ScheduleState
) -> SplitDay | None:
    days = _ordered_days(session, user_id, state.active_split_id)
    if not days:
        return None
    if state.cursor_split_day_id is None or state.cursor_effective_date is None:
        return next((day for day in days if day.recommended_weekday == local_date.weekday()), None)
    cursor_index = next(
        (index for index, day in enumerate(days) if day.id == state.cursor_split_day_id), None
    )
    if cursor_index is None:
        return None
    if local_date == state.cursor_effective_date:
        return days[cursor_index]
    if local_date < state.cursor_effective_date:
        return next((day for day in days if day.recommended_weekday == local_date.weekday()), None)
    weekdays = {day.recommended_weekday for day in days if day.recommended_weekday is not None}
    if local_date.weekday() not in weekdays:
        return None
    opportunities = 0
    candidate = state.cursor_effective_date + timedelta(days=1)
    while candidate <= local_date:
        if candidate.weekday() in weekdays:
            opportunities += 1
        candidate += timedelta(days=1)
    return days[(cursor_index + opportunities) % len(days)]


def resolve_effective_plan(session: Session, user_id: str, local_date: date) -> EffectivePlan:
    state = require_schedule(session, user_id)
    planned = _cursor_planned_day(session, user_id, local_date, state)
    override = repository.override_for_date(session, user_id, local_date)
    effective = planned
    if override is not None:
        if override.action in {OverrideAction.REST, OverrideAction.SKIP}:
            effective = None
        elif override.effective_split_day_id is not None:
            effective = repository.split_day(session, user_id, override.effective_split_day_id)
    daily = repository.exercise_plan(session, user_id, local_date)
    daily_items = repository.exercise_plan_items(session, daily.id) if daily else []
    return EffectivePlan(local_date, planned, effective, override, daily, daily_items)


def _muscle_target(link: object) -> dict[str, object]:
    muscle = link.muscle_group  # type: ignore[attr-defined]
    return {
        "slug": muscle.slug,
        "display_name": muscle.display_name,
        "role": link.role.value,  # type: ignore[attr-defined]
        "intensity": float(link.contribution),  # type: ignore[attr-defined]
        "svg_region_ids": muscle.svg_region_ids,
    }


def _template_item(item: WorkoutTemplateItem, user_id: str) -> dict[str, object]:
    return {
        "id": item.id,
        "exercise": serialize_exercise(item.exercise, user_id),
        "sequence": item.sequence,
        "item_type": item.item_type.value,
        "sets": item.sets,
        "rep_min": item.rep_min,
        "rep_max": item.rep_max,
        "duration_seconds": item.duration_seconds,
        "distance_meters": float(item.distance_meters)
        if item.distance_meters is not None
        else None,
        "rounds_target": item.rounds_target,
        "rest_seconds": item.rest_seconds,
        "target_rir": float(item.target_rir) if item.target_rir is not None else None,
        "superset_group": item.superset_group,
        "notes": item.notes,
        "optional": item.optional,
        "alternatives": [serialize_exercise(alt.exercise, user_id) for alt in item.alternatives],
    }


def serialize_scheduled_day(day: SplitDay | None, user_id: str) -> dict[str, object] | None:
    if day is None:
        return None
    return {
        "id": day.id,
        "name": day.name,
        "day_type": day.day_type,
        "sequence": day.sequence,
        "is_optional": day.is_optional,
        "items": [_template_item(item, user_id) for item in day.items],
    }


def _template_plan(day: SplitDay | None, user_id: str) -> list[dict[str, object]]:
    if day is None:
        return []
    return [
        {
            "id": item.id,
            "source_template_item_id": item.id,
            "exercise": serialize_exercise(item.exercise, user_id),
            "sequence": item.sequence - 1,
            "item_type": item.item_type.value,
            "planned_sets": item.sets,
            "rep_min": item.rep_min,
            "rep_max": item.rep_max,
            "duration_seconds": item.duration_seconds,
            "distance_meters": float(item.distance_meters)
            if item.distance_meters is not None
            else None,
            "rounds_target": item.rounds_target,
            "rest_seconds": item.rest_seconds,
            "target_rir": float(item.target_rir) if item.target_rir is not None else None,
            "superset_group": item.superset_group,
            "optional": item.optional,
            "notes": item.notes,
        }
        for item in day.items
    ]


def exercise_plan_payload(plan: EffectivePlan, user_id: str) -> list[dict[str, object]]:
    if plan.daily_plan is None:
        return _template_plan(plan.effective_day, user_id)
    return [
        {
            "id": item.id,
            "source_template_item_id": item.source_template_item_id,
            "exercise": serialize_exercise(exercise, user_id),
            "sequence": item.sequence,
            "item_type": item.item_type.value,
            "planned_sets": item.planned_sets,
            "rep_min": item.rep_min,
            "rep_max": item.rep_max,
            "duration_seconds": item.duration_seconds,
            "distance_meters": float(item.distance_meters)
            if item.distance_meters is not None
            else None,
            "rounds_target": item.rounds_target,
            "rest_seconds": item.rest_seconds,
            "target_rir": float(item.target_rir) if item.target_rir is not None else None,
            "superset_group": item.superset_group,
            "optional": item.optional,
            "notes": item.notes,
        }
        for item, exercise in plan.daily_items
    ]


def aggregate_muscle_targets(plan_items: Iterable[tuple[Exercise, int]]) -> list[dict[str, object]]:
    strongest: dict[str, object] = {}
    rank = {MuscleRole.STABILIZER: 0, MuscleRole.SECONDARY: 1, MuscleRole.PRIMARY: 2}
    for exercise, _sets in plan_items:
        for link in exercise.muscle_links:
            current = strongest.get(link.muscle_group_id)
            if current is None or rank[link.role] > rank[current.role]:  # type: ignore[attr-defined]
                strongest[link.muscle_group_id] = link
    return sorted(
        (_muscle_target(link) for link in strongest.values()),
        key=lambda target: (
            -cast(float, target["intensity"]),
            str(target["display_name"]),
        ),
    )


def _override_payload(row: DailyPlanOverride | None) -> dict[str, object] | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "local_date": row.local_date.isoformat(),
        "action": row.action.value,
        "planned_split_day_id": row.planned_split_day_id,
        "effective_split_day_id": row.effective_split_day_id,
        "swap_target_local_date": (
            row.swap_target_local_date.isoformat() if row.swap_target_local_date else None
        ),
        "schedule_effect": row.schedule_effect.value,
        "reason": row.reason,
        "version": row.version,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def _avatar_payload(settings: AvatarSettings | None) -> dict[str, object]:
    if settings is None:
        return {
            "base_presentation": "male",
            "skin_tone": "rich",
            "hairstyle": "short_coils",
            "hair_color": "black",
            "outfit_style": "training_tee",
            "outfit_palette": "violet",
            "accessory": "none",
            "background": "gradient",
            "aura_style": "standard",
            "aura_enabled": True,
        }
    return {
        "base_presentation": settings.base_presentation.value,
        "skin_tone": settings.skin_tone,
        "hairstyle": settings.hairstyle,
        "hair_color": settings.hair_color,
        "outfit_style": settings.outfit_style,
        "outfit_palette": settings.outfit_palette,
        "accessory": settings.accessory,
        "background": settings.background,
        "aura_style": settings.aura_style,
        "aura_enabled": settings.aura_enabled,
    }


def today_payload(session: Session, user_id: str, local_date: date) -> dict[str, object]:
    profile = repository.profile(session, user_id)
    user = repository.user(session, user_id)
    if profile is None or profile.settings is None or user is None:
        raise ApiError(503, "DATA_NOT_INITIALIZED", "Account data is unavailable.")
    plan = resolve_effective_plan(session, user_id, local_date)
    active = repository.active_session(session, user_id, local_date)
    if plan.daily_plan is not None:
        muscle_source = [(exercise, item.planned_sets) for item, exercise in plan.daily_items]
    else:
        muscle_source = [
            (item.exercise, item.sets)
            for item in (plan.effective_day.items if plan.effective_day else [])
        ]
    from levels_api.features.sessions.service import session_payload

    return {
        "local_date": local_date.isoformat(),
        "user": current_user_payload(user),
        "planned_day": serialize_scheduled_day(plan.planned_day, user_id),
        "effective_day": serialize_scheduled_day(plan.effective_day, user_id),
        "override": _override_payload(plan.override),
        "schedule_version": require_schedule(session, user_id).version,
        "exercise_plan": exercise_plan_payload(plan, user_id),
        "active_session": session_payload(active) if active is not None else None,
        "muscle_targets": aggregate_muscle_targets(muscle_source),
        "water": serialize_water_day(
            local_date,
            repository.water_entries(session, user_id, local_date),
            profile.settings.default_water_goal_ml,
        ),
        "latest_achievements": serialize_public_achievements(
            repository.latest_achievements(session, user_id)
        ),
        "avatar": _avatar_payload(repository.avatar(session, user_id)),
        "streak": streak_summary(session, user_id, through_date=local_date),
    }


def _ensure_unstarted(session: Session, user_id: str, local_date: date) -> None:
    if repository.active_session(session, user_id, local_date) is not None:
        raise ApiError(409, "SESSION_ALREADY_STARTED", "This plan already has a started session.")


def _bump(
    session: Session,
    user_id: str,
    expected_version: int,
    **values: object,
) -> ScheduleState:
    state = repository.update_schedule(session, user_id, expected_version, **values)
    if state is None:
        raise _conflict()
    return state


def put_override(
    session: Session,
    user_id: str,
    write: TodayOverrideRequest,
    idempotency_key: str,
) -> None:
    operation = "today.override"
    if replay_receipt(session, user_id, operation, idempotency_key, write) is not None:
        return
    state = require_schedule(session, user_id)
    if state.version != write.expected_version:
        raise _conflict()
    _ensure_unstarted(session, user_id, write.local_date)
    if repository.override_for_date(session, user_id, write.local_date) is not None:
        raise ApiError(409, "OVERRIDE_EXISTS", "Remove the existing override before replacing it.")
    plan = resolve_effective_plan(session, user_id, write.local_date)
    selected = None
    if write.effective_split_day_id is not None:
        selected = repository.split_day(session, user_id, write.effective_split_day_id)
        if selected is None:
            raise ApiError(404, "NOT_FOUND", "The selected split day was not found.")
    schedule_values: dict[str, object] = {}
    paired: DailyPlanOverride | None = None
    group_id: str | None = None
    if write.schedule_effect == "continue_from_here":
        assert selected is not None
        days = _ordered_days(session, user_id, selected.split_id)
        schedule_values = {
            "active_split_id": selected.split_id,
            "cursor_split_day_id": _next_day(days, selected).id,
            "cursor_effective_date": _next_opportunity(write.local_date, days),
        }
    elif write.action == "swap":
        assert write.swap_target_local_date is not None and selected is not None
        if write.swap_target_local_date <= write.local_date:
            raise ApiError(422, "VALIDATION_ERROR", "Swap target must be a future date.")
        _ensure_unstarted(session, user_id, write.swap_target_local_date)
        if repository.override_for_date(session, user_id, write.swap_target_local_date) is not None:
            raise ApiError(409, "OVERRIDE_EXISTS", "The swap target already has an override.")
        target = resolve_effective_plan(session, user_id, write.swap_target_local_date)
        if target.planned_day is None or plan.planned_day is None:
            raise ApiError(422, "VALIDATION_ERROR", "Both swap dates must be training days.")
        if target.planned_day.id != selected.id:
            raise ApiError(
                422, "VALIDATION_ERROR", "The selected workout does not match the target date."
            )
        group_id = str(uuid4())
        paired = DailyPlanOverride(
            user_id=user_id,
            local_date=write.swap_target_local_date,
            action=OverrideAction.SWAP,
            planned_split_day_id=target.planned_day.id,
            effective_split_day_id=plan.planned_day.id,
            swap_target_local_date=write.local_date,
            schedule_effect=ScheduleEffect.SWAP_FORWARD,
            reason=write.reason,
            swap_group_id=group_id,
            version=0,
        )
    state = _bump(session, user_id, write.expected_version, **schedule_values)
    row = DailyPlanOverride(
        user_id=user_id,
        local_date=write.local_date,
        action=OverrideAction(write.action),
        planned_split_day_id=plan.planned_day.id if plan.planned_day else None,
        effective_split_day_id=selected.id if selected else None,
        swap_target_local_date=write.swap_target_local_date,
        schedule_effect=ScheduleEffect(write.schedule_effect),
        reason=write.reason,
        swap_group_id=group_id,
        version=0,
    )
    session.add(row)
    if paired is not None:
        session.add(paired)
    session.flush()
    record_receipt(
        session,
        user_id,
        operation,
        idempotency_key,
        write,
        result_resource_id=row.id,
        result_version=state.version,
        status_code=200,
    )


def skip_today(
    session: Session,
    user_id: str,
    write: SkipTodayRequest,
    idempotency_key: str,
) -> None:
    operation = "today.skip"
    if replay_receipt(session, user_id, operation, idempotency_key, write) is not None:
        return
    state = require_schedule(session, user_id)
    if state.version != write.expected_version:
        raise _conflict()
    _ensure_unstarted(session, user_id, write.local_date)
    if repository.override_for_date(session, user_id, write.local_date) is not None:
        raise ApiError(409, "OVERRIDE_EXISTS", "This date already has an override.")
    plan = resolve_effective_plan(session, user_id, write.local_date)
    if plan.planned_day is None:
        raise ApiError(422, "VALIDATION_ERROR", "A rest day cannot be skipped.")
    days = _ordered_days(session, user_id, state.active_split_id)
    cursor = (
        _next_day(days, plan.planned_day)
        if write.schedule_effect == "advance"
        else plan.planned_day
    )
    next_date = _next_opportunity(write.local_date, days)
    state = _bump(
        session,
        user_id,
        write.expected_version,
        cursor_split_day_id=cursor.id,
        cursor_effective_date=next_date,
    )
    row = DailyPlanOverride(
        user_id=user_id,
        local_date=write.local_date,
        action=OverrideAction.SKIP,
        planned_split_day_id=plan.planned_day.id,
        effective_split_day_id=None,
        swap_target_local_date=None,
        schedule_effect=ScheduleEffect(write.schedule_effect),
        reason=write.reason,
        swap_group_id=None,
        version=0,
    )
    session.add(row)
    session.flush()
    record_receipt(
        session,
        user_id,
        operation,
        idempotency_key,
        write,
        result_resource_id=row.id,
        result_version=state.version,
        status_code=200,
    )


def delete_override(
    session: Session, user_id: str, local_date: date, expected_version: int
) -> None:
    state = require_schedule(session, user_id)
    if state.version != expected_version:
        raise _conflict()
    _ensure_unstarted(session, user_id, local_date)
    row = repository.override_for_date(session, user_id, local_date)
    if row is None:
        raise ApiError(404, "NOT_FOUND", "The requested override was not found.")
    rows = (
        repository.overrides_for_group(session, user_id, row.swap_group_id)
        if row.swap_group_id
        else [row]
    )
    schedule_values: dict[str, object] = {}
    if (
        row.schedule_effect
        in {
            ScheduleEffect.CONTINUE_FROM_HERE,
            ScheduleEffect.ADVANCE,
            ScheduleEffect.KEEP,
        }
        and row.planned_split_day_id is not None
    ):
        planned = repository.split_day(session, user_id, row.planned_split_day_id)
        if planned is not None:
            schedule_values = {
                "active_split_id": planned.split_id,
                "cursor_split_day_id": planned.id,
                "cursor_effective_date": row.local_date,
            }
    _bump(session, user_id, expected_version, **schedule_values)
    for item in rows:
        session.delete(item)
    session.flush()


def _replace_daily_items(
    session: Session,
    plan: DailyExercisePlan,
    write: TodayExercisePlanUpdate,
    exercises: dict[str, Exercise],
) -> None:
    session.execute(
        delete(DailyExercisePlanItem).where(DailyExercisePlanItem.daily_exercise_plan_id == plan.id)
    )
    for item in write.items:
        session.add(
            DailyExercisePlanItem(
                daily_exercise_plan_id=plan.id,
                source_template_item_id=item.source_template_item_id,
                exercise_id=exercises[item.exercise_id].id,
                sequence=item.sequence,
                item_type=item.item_type,
                planned_sets=item.planned_sets,
                rep_min=item.rep_min,
                rep_max=item.rep_max,
                duration_seconds=item.duration_seconds,
                distance_meters=(
                    Decimal(str(item.distance_meters)) if item.distance_meters is not None else None
                ),
                rounds_target=item.rounds_target,
                rest_seconds=item.rest_seconds,
                target_rir=(Decimal(str(item.target_rir)) if item.target_rir is not None else None),
                superset_group=item.superset_group,
                optional=item.optional,
                notes=item.notes,
            )
        )


def _save_template(
    session: Session,
    day: SplitDay,
    write: TodayExercisePlanUpdate,
) -> None:
    by_id = {item.id: item for item in day.items}
    supplied_ids = {
        item.source_template_item_id for item in write.items if item.source_template_item_id
    }
    if not supplied_ids.issubset(by_id):
        raise ApiError(404, "NOT_FOUND", "A source template item was not found in this split day.")
    for existing in day.items:
        existing.sequence += 1000
    session.flush()
    for input_item in write.items:
        template = by_id.get(input_item.source_template_item_id or "")
        if template is None:
            template = WorkoutTemplateItem(split_day_id=day.id)
            session.add(template)
        template.exercise_id = input_item.exercise_id
        template.sequence = input_item.sequence + 1
        template.item_type = input_item.item_type
        template.sets = input_item.planned_sets
        template.rep_min = input_item.rep_min
        template.rep_max = input_item.rep_max
        template.duration_seconds = input_item.duration_seconds
        template.distance_meters = (
            Decimal(str(input_item.distance_meters))
            if input_item.distance_meters is not None
            else None
        )
        template.rounds_target = input_item.rounds_target
        template.rest_seconds = input_item.rest_seconds
        template.target_rir = (
            Decimal(str(input_item.target_rir)) if input_item.target_rir is not None else None
        )
        template.superset_group = input_item.superset_group
        template.optional = input_item.optional
        template.notes = input_item.notes
    removed = [item for item_id, item in by_id.items() if item_id not in supplied_ids]
    for item in removed:
        archive_template_item(session, day.split.user_id, item)


def replace_exercise_plan(
    session: Session,
    user_id: str,
    write: TodayExercisePlanUpdate,
    idempotency_key: str,
) -> None:
    operation = "today.exercises"
    if replay_receipt(session, user_id, operation, idempotency_key, write) is not None:
        return
    state = require_schedule(session, user_id)
    if state.version != write.expected_version:
        raise _conflict()
    _ensure_unstarted(session, user_id, write.local_date)
    exercises: dict[str, Exercise] = {}
    for item in write.items:
        exercise = repository.available_exercise(session, user_id, item.exercise_id)
        if exercise is None:
            raise ApiError(404, "NOT_FOUND", "An exercise was not found.")
        exercises[item.exercise_id] = exercise
    effective = resolve_effective_plan(session, user_id, write.local_date)
    source_day = effective.effective_day
    if write.source_split_day_id is not None:
        source_day = repository.split_day(session, user_id, write.source_split_day_id)
        if source_day is None:
            raise ApiError(404, "NOT_FOUND", "The source split day was not found.")
    if write.scope == "save_to_split" and source_day is None:
        raise ApiError(422, "VALIDATION_ERROR", "A rest day cannot be saved to a split.")
    state = _bump(session, user_id, write.expected_version)
    plan = repository.exercise_plan(session, user_id, write.local_date)
    if plan is None:
        plan = DailyExercisePlan(
            user_id=user_id,
            local_date=write.local_date,
            source_split_day_id=source_day.id if source_day else None,
            version=0,
        )
        session.add(plan)
        session.flush()
    else:
        plan.source_split_day_id = source_day.id if source_day else None
        plan.version += 1
    _replace_daily_items(session, plan, write, exercises)
    if write.scope == "save_to_split":
        assert source_day is not None
        _save_template(session, source_day, write)
    session.flush()
    record_receipt(
        session,
        user_id,
        operation,
        idempotency_key,
        write,
        result_resource_id=plan.id,
        result_version=state.version,
        status_code=200,
    )
