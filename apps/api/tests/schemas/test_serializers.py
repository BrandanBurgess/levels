from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from levels_api.models import (
    Achievement,
    PreferredUnits,
    Profile,
    PublicVisibility,
    SessionExercise,
    SessionStatus,
    SetLog,
    SetType,
    VisibilitySettings,
    WaterLog,
    WaterSource,
    WorkoutSession,
)
from levels_api.schemas import (
    serialize_admin_profile,
    serialize_admin_session,
    serialize_public_achievements,
    serialize_public_profile,
    serialize_public_session,
    serialize_water_day,
)
from levels_api.schemas.dtos import PublicProfileDto

NOW = datetime(2026, 7, 13, 20, 0, tzinfo=UTC)


def _profile() -> Profile:
    profile = Profile(
        id="profile-1",
        display_name="Brandan Burgess",
        height_cm=179,
        body_weight_kg=Decimal("79.38"),
        preferred_units=PreferredUnits.IMPERIAL,
        timezone="America/Toronto",
        avatar_variant="brandan-original-v1",
    )
    profile.visibility = VisibilitySettings(
        id="visibility-1",
        profile_id=profile.id,
        show_height=True,
        show_body_weight=False,
        show_water=False,
        show_session_summaries=True,
        show_set_details=False,
        show_public_notes=False,
        show_progress_charts=True,
        show_personal_records=True,
        show_readiness=False,
    )
    return profile


def _session(visibility: PublicVisibility = PublicVisibility.FULL) -> WorkoutSession:
    set_log = SetLog(
        id="set-1",
        session_exercise_id="session-exercise-1",
        sequence=1,
        set_type=SetType.WORKING,
        load_kg=Decimal("100"),
        reps=8,
        rir=Decimal("2"),
        duration_seconds=None,
        distance_meters=None,
        rounds=None,
        bodyweight_assistance_kg=Decimal("12"),
        form_quality=4,
        pain_flag=False,
        completed_at=NOW,
        notes="private set note",
        deleted_at=None,
        idempotency_key="private-idempotency-key",
    )
    exercise = SessionExercise(
        id="session-exercise-1",
        workout_session_id="session-1",
        exercise_id="incline_barbell_bench_press",
        source_template_item_id=None,
        sequence=1,
        display_name_snapshot="Incline Barbell Bench Press",
        variation_group_snapshot="incline_press",
        rep_min_snapshot=5,
        rep_max_snapshot=8,
        target_rir_snapshot=Decimal("2"),
        notes="private exercise note",
        substitution_reason="private substitution reason",
        sets=[set_log],
    )
    return WorkoutSession(
        id="session-1",
        split_day_id="day-1",
        session_date_local=date(2026, 7, 13),
        started_at=NOW,
        completed_at=NOW,
        status=SessionStatus.COMPLETED,
        title="Upper A",
        public_visibility=visibility,
        perceived_effort=8,
        notes_private="private session note",
        notes_public="public session note",
        deleted_at=None,
        exercises=[exercise],
    )


def _visibility(**overrides: bool) -> VisibilitySettings:
    values = {
        "show_height": True,
        "show_body_weight": False,
        "show_water": False,
        "show_session_summaries": True,
        "show_set_details": False,
        "show_public_notes": False,
        "show_progress_charts": True,
        "show_personal_records": True,
        "show_readiness": False,
        **overrides,
    }
    return VisibilitySettings(id="visibility-1", profile_id="profile-1", **values)


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_all_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_all_keys(item) for item in value))
    return set()


def test_public_profile_omits_hidden_values_and_internal_identity() -> None:
    result = serialize_public_profile(_profile())

    assert result["display_name"] == "Brandan Burgess"
    assert result["height_cm"] == 179
    assert "body_weight_kg" not in result
    assert "id" not in result
    assert "visibility" not in result


def test_admin_profile_uses_separate_explicit_shape() -> None:
    result = serialize_admin_profile(_profile())

    assert result["id"] == "profile-1"
    assert result["body_weight_kg"] == 79.38
    assert set(result) == {
        "id",
        "display_name",
        "height_cm",
        "body_weight_kg",
        "preferred_units",
        "timezone",
        "avatar_variant",
    }


def test_private_and_disabled_sessions_are_not_serialized_publicly() -> None:
    assert serialize_public_session(_session(PublicVisibility.PRIVATE), _visibility()) is None
    assert (
        serialize_public_session(
            _session(PublicVisibility.FULL), _visibility(show_session_summaries=False)
        )
        is None
    )


def test_summary_and_full_visibility_apply_nested_privacy_flags() -> None:
    summary = serialize_public_session(_session(PublicVisibility.SUMMARY), _visibility())
    assert summary is not None
    assert summary["exercises"] == []
    assert "notes_public" not in summary

    full = serialize_public_session(
        _session(), _visibility(show_set_details=True, show_public_notes=True)
    )
    assert full is not None
    assert full["notes_public"] == "public session note"
    assert full["exercises"][0]["sets"][0]["load_kg"] == 100.0
    forbidden = {
        "notes_private",
        "notes",
        "idempotency_key",
        "bodyweight_assistance_kg",
        "deleted_at",
        "source_template_item_id",
        "substitution_reason",
    }
    assert _all_keys(full).isdisjoint(forbidden)


def test_admin_session_remains_contract_allowlisted() -> None:
    result = serialize_admin_session(_session())

    assert result["notes_private"] == "private session note"
    assert result["exercises"][0]["substitution_reason"] == "private substitution reason"
    assert result["exercises"][0]["sets"][0]["notes"] == "private set note"
    assert _all_keys(result).isdisjoint(
        {"idempotency_key", "bodyweight_assistance_kg", "deleted_at"}
    )


def test_water_serializer_excludes_source_and_notes() -> None:
    entry = WaterLog(
        id="water-1",
        occurred_at=NOW,
        local_date=date(2026, 7, 13),
        amount_ml=500,
        source=WaterSource.CUSTOM,
        note="private water note",
        created_at=NOW,
    )
    result = serialize_water_day(date(2026, 7, 13), [entry], 2000)

    assert result["total_ml"] == 500
    assert result["progress_ratio"] == 0.25
    assert set(result["entries"][0]) == {"id", "amount_ml", "occurred_at"}


def test_only_public_achievements_are_serialized() -> None:
    public = Achievement(
        id="achievement-public",
        achievement_type="personal_record",
        exercise_id="exercise-1",
        set_log_id="set-1",
        title="New record",
        message="A public milestone",
        achieved_at=NOW,
        public=True,
        idempotency_key="achievement-public-key",
    )
    private = Achievement(
        id="achievement-private",
        achievement_type="personal_record",
        exercise_id="exercise-1",
        set_log_id="set-2",
        title="Private record",
        message="A hidden milestone",
        achieved_at=NOW,
        public=False,
        idempotency_key="achievement-private-key",
    )

    result = serialize_public_achievements([private, public])
    assert [item["id"] for item in result] == ["achievement-public"]
    assert "idempotency_key" not in result[0]
    assert "set_log_id" not in result[0]


def test_dtos_forbid_accidental_extra_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PublicProfileDto(
            display_name="Brandan",
            preferred_units="imperial",
            timezone="America/Toronto",
            avatar_variant="brandan-original-v1",
            password_hash="must never serialize",  # type: ignore[call-arg]
        )
