from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from levels_api.errors import ApiError
from levels_api.features.profile.service import require_profile
from levels_api.features.today.repository import scheduled_day
from levels_api.models import Exercise, ReadinessLog, SessionExercise, SplitDay

from . import repository

Suggestion = dict[str, Any]


def _base(
    exercise: Exercise,
    suggestion_type: str,
    confidence: str,
    explanation: list[str],
    sources: list[str],
    *,
    delta: Decimal | int | None = None,
    delta_unit: str | None = None,
) -> Suggestion:
    return {
        "exercise_id": exercise.id,
        "exercise_name": exercise.name,
        "suggestion_type": suggestion_type,
        "suggested_delta": float(delta) if delta is not None else None,
        "delta_unit": delta_unit,
        "confidence": confidence,
        "explanation": explanation,
        "source_session_ids": sources,
    }


def _session_total(item: SessionExercise) -> int:
    return sum(set_log.reps or 0 for set_log in repository.active_sets(item))


def _poor_readiness(readiness: ReadinessLog | None) -> bool:
    return readiness is not None and (
        readiness.energy <= 2
        or readiness.soreness >= 4
        or readiness.sleep_quality <= 2
        or readiness.pain_flag
    )


def suggestion_for_exercise(
    session: Session,
    exercise: Exercise,
    *,
    owner: bool,
    readiness: ReadinessLog | None,
    default_increment: Decimal,
    target_rep_max: int | None,
    target_rir: Decimal,
) -> Suggestion:
    history = repository.recent_exercise_sessions(session, exercise.id, owner=owner)
    sources = [item.workout_session_id for item in history]
    if len(history) < 2:
        return _base(
            exercise,
            "insufficient_data",
            "insufficient",
            [
                f"{len(history)} comparable completed session(s) found; at least 2 are required.",
                "Log consistent working sets before changing the progression target.",
            ],
            sources,
        )

    latest_sets = repository.active_sets(history[0])
    confidence = "high" if len(history) >= 3 else "medium"
    if any(set_log.pain_flag for set_log in latest_sets) or (
        readiness is not None and readiness.pain_flag
    ):
        return _base(
            exercise,
            "no_progression",
            confidence,
            [
                "Pain was recorded in the latest evidence, so overload is paused.",
                "Repeat a comfortable option or choose an easier variation; "
                "this is not medical advice.",
            ],
            sources,
        )
    if any(
        set_log.form_quality is not None and set_log.form_quality <= 2 for set_log in latest_sets
    ):
        return _base(
            exercise,
            "maintain",
            confidence,
            [
                "Latest form quality included a score of 2 or lower.",
                "Keep the current target and prioritize controlled technique.",
            ],
            sources,
        )
    if _poor_readiness(readiness):
        return _base(
            exercise,
            "maintain",
            confidence,
            [
                "Today’s readiness check is below the overload threshold.",
                "Maintain the recent target rather than increasing load or volume.",
            ],
            sources,
        )
    if not exercise.automatic_progression_enabled:
        return _base(
            exercise,
            "no_progression",
            confidence,
            ["Automatic progression is disabled for this exercise."],
            sources,
        )

    rep_max = target_rep_max or history[0].rep_max_snapshot or exercise.default_rep_max
    all_at_top = (
        bool(latest_sets)
        and rep_max is not None
        and all(
            set_log.reps is not None
            and set_log.reps >= rep_max
            and set_log.rir is not None
            and set_log.rir >= target_rir
            and (set_log.form_quality is None or set_log.form_quality >= 3)
            for set_log in latest_sets
        )
    )
    if all_at_top and exercise.measurement_type.value == "load_reps":
        increment = exercise.progression_increment_kg or default_increment
        return _base(
            exercise,
            "increase_load",
            confidence,
            [
                f"All {len(latest_sets)} latest working set(s) reached {rep_max} reps.",
                f"RIR met the {float(target_rir):g} target with acceptable form and no pain.",
                "Use only the smallest configured load increment; no max attempt is suggested.",
            ],
            sources,
            delta=increment,
            delta_unit="kg",
        )

    totals = [_session_total(item) for item in history]
    if len(totals) >= 3 and totals[0] < totals[1] < totals[2]:
        return _base(
            exercise,
            "maintain",
            confidence,
            [
                "Total reps declined across two comparisons: "
                f"{totals[2]}, {totals[1]}, {totals[0]}.",
                "Maintain the target and consider reducing one set if recovery remains limited.",
            ],
            sources,
        )
    if totals[0] > totals[1]:
        return _base(
            exercise,
            "repeat_load",
            confidence,
            [
                f"Total reps improved from {totals[1]} to {totals[0]} "
                "at the recent working target.",
                "Repeat the load and make the sets consistent before increasing it.",
            ],
            sources,
        )
    return _base(
        exercise,
        "add_rep",
        confidence,
        [
            f"Recent total reps were {totals[1]} and {totals[0]} without a top-of-range result.",
            "Aim for one additional rep while keeping load, form, and pain status stable.",
        ],
        sources,
        delta=1,
        delta_unit="rep",
    )


def _target_day(session: Session, local_date: date, split_day_id: str | None) -> SplitDay | None:
    profile = require_profile(session)
    assert profile.settings is not None
    if split_day_id is not None:
        day = session.get(SplitDay, split_day_id)
        if day is None:
            raise ApiError(400, "VALIDATION_ERROR", "The selected split day does not exist.")
        return day
    return scheduled_day(
        session,
        profile.settings.active_split_id,
        local_date.weekday(),
    )


def growth_suggestions(
    session: Session,
    local_date: date,
    *,
    split_day_id: str | None,
    owner: bool,
) -> list[Suggestion]:
    profile = require_profile(session)
    assert profile.settings is not None and profile.visibility is not None
    if not owner and not profile.visibility.show_progress_charts:
        return []
    day = _target_day(session, local_date, split_day_id)
    if day is None:
        return []
    readiness = (
        repository.readiness_on(session, local_date)
        if owner or profile.visibility.show_readiness
        else None
    )
    seen: set[str] = set()
    result: list[Suggestion] = []
    for item in day.items:
        if item.exercise_id in seen:
            continue
        seen.add(item.exercise_id)
        result.append(
            suggestion_for_exercise(
                session,
                item.exercise,
                owner=owner,
                readiness=readiness,
                default_increment=profile.settings.default_load_increment_kg,
                target_rep_max=item.rep_max,
                target_rir=item.target_rir or profile.settings.default_target_rir,
            )
        )
    return result
