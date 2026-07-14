from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import Engine, create_engine, event, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from levels_api.models import (
    AppSettings,
    Base,
    Exercise,
    MeasurementType,
    PreferredUnits,
    Profile,
    PublicVisibility,
    SessionExercise,
    SessionStatus,
    SetLog,
    SetType,
    Split,
    SplitDay,
    VisibilitySettings,
    WorkoutSession,
)


@pytest.fixture
def engine() -> Iterator[Engine]:
    database = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(database, "connect")
    def enable_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(database)
    yield database
    database.dispose()


def test_metadata_contains_complete_schema(engine: Engine) -> None:
    table_names = set(inspect(engine).get_table_names())

    assert table_names == {
        "achievements",
        "app_settings",
        "exercise_muscles",
        "exercises",
        "muscle_groups",
        "personal_records",
        "profiles",
        "progression_suggestions",
        "readiness_logs",
        "session_exercises",
        "set_logs",
        "split_days",
        "splits",
        "template_alternatives",
        "visibility_settings",
        "water_logs",
        "workout_sessions",
        "workout_template_items",
    }


def test_profile_defaults_and_json_values_are_independent(engine: Engine) -> None:
    with Session(engine) as session:
        profile = Profile(display_name="Brandan", preferred_units=PreferredUnits.IMPERIAL)
        profile.visibility = VisibilitySettings()
        profile.settings = AppSettings()
        session.add(profile)
        session.commit()

        assert profile.timezone == "America/Toronto"
        assert profile.visibility.show_body_weight is False
        assert profile.settings.water_quick_add_ml == [250, 500, 750]
        assert session.scalar(text("SELECT preferred_units FROM profiles")) == "imperial"


def test_database_rejects_out_of_range_profile_height(engine: Engine) -> None:
    with Session(engine) as session:
        session.add(
            Profile(
                display_name="Brandan",
                height_cm=99,
                preferred_units=PreferredUnits.IMPERIAL,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_session_exercise_is_a_historical_snapshot(engine: Engine) -> None:
    with Session(engine) as session:
        exercise = Exercise(
            slug="incline_press",
            name="Incline Press",
            aliases=[],
            variation_group="incline_press",
            movement_pattern="horizontal_push",
            equipment="barbell",
            measurement_type=MeasurementType.LOAD_REPS,
            compound=True,
            unilateral=False,
        )
        split = Split(name="Upper Lower", slug="upper-lower")
        day = SplitDay(name="Upper A", day_type="upper", sequence=1)
        split.days.append(day)
        workout = WorkoutSession(
            split_day=day,
            session_date_local=date(2026, 7, 13),
            status=SessionStatus.IN_PROGRESS,
            title="Upper A",
            public_visibility=PublicVisibility.PRIVATE,
        )
        snapshot = SessionExercise(
            exercise=exercise,
            sequence=1,
            display_name_snapshot="Incline Press",
            variation_group_snapshot="incline_press",
        )
        snapshot.sets.append(
            SetLog(
                sequence=1,
                set_type=SetType.WORKING,
                load_kg=Decimal("70"),
                reps=8,
                idempotency_key="set-key-0001",
            )
        )
        workout.exercises.append(snapshot)
        session.add(workout)
        session.commit()

        exercise.name = "Renamed Incline Press"
        session.commit()
        session.expire_all()

        stored = session.scalar(select(SessionExercise))
        assert stored is not None
        assert stored.display_name_snapshot == "Incline Press"
        assert stored.exercise.name == "Renamed Incline Press"


def test_set_idempotency_key_is_unique(engine: Engine) -> None:
    with Session(engine) as session:
        exercise = Exercise(
            slug="cable_curl",
            name="Cable Curl",
            aliases=[],
            variation_group="curl",
            movement_pattern="isolation",
            equipment="cable",
            measurement_type=MeasurementType.LOAD_REPS,
            compound=False,
            unilateral=False,
        )
        workout = WorkoutSession(
            session_date_local=date(2026, 7, 13),
            status=SessionStatus.IN_PROGRESS,
            title="Arms",
            public_visibility=PublicVisibility.PRIVATE,
        )
        first = SessionExercise(
            exercise=exercise,
            sequence=1,
            display_name_snapshot="Cable Curl",
            variation_group_snapshot="curl",
        )
        first.sets.append(
            SetLog(sequence=1, set_type=SetType.WORKING, idempotency_key="duplicate-key")
        )
        second = SessionExercise(
            exercise=exercise,
            sequence=2,
            display_name_snapshot="Cable Curl",
            variation_group_snapshot="curl",
        )
        second.sets.append(
            SetLog(sequence=1, set_type=SetType.WORKING, idempotency_key="duplicate-key")
        )
        workout.exercises.extend([first, second])
        session.add(workout)

        with pytest.raises(IntegrityError):
            session.commit()
