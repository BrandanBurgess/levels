from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from flask import Flask
from sqlalchemy import select
from sqlalchemy.orm import Session

from levels_api import Settings, create_app
from levels_api.auth.service import create_access_token
from levels_api.database import get_engine
from levels_api.models import (
    Achievement,
    Base,
    PublicVisibility,
    SessionStatus,
    VisibilitySettings,
    WaterLog,
    WaterSource,
    WorkoutSession,
)
from levels_api.seed import seed_session

JWT_SECRET = "tests-only-jwt-signing-key-32-characters-long"
MONDAY = date(2026, 7, 13)


@pytest.fixture
def app(tmp_path: Path) -> Iterator[Flask]:
    application = create_app(
        Settings.for_testing(
            f"sqlite+pysqlite:///{tmp_path / 'today.db'}",
            admin_username="brandan",
            admin_password_hash="$argon2id$unused-in-route-tests",
            jwt_secret_key=JWT_SECRET,
        )
    )
    with application.app_context():
        engine = get_engine()
        Base.metadata.create_all(engine)
        with Session(engine) as session, session.begin():
            seed_session(session)
            session.add(
                Achievement(
                    achievement_type="personal_record",
                    exercise_id="incline_barbell_bench_press",
                    set_log_id=None,
                    title="New incline record",
                    message="A public achievement",
                    achieved_at=datetime(2026, 7, 13, 18, 0, tzinfo=UTC),
                    public=True,
                    idempotency_key="today-achievement",
                )
            )
        token, _ = create_access_token("brandan")
        application.config["TEST_ACCESS_TOKEN"] = token
    yield application
    with application.app_context():
        get_engine().dispose()


def _auth(app: Flask) -> dict[str, str]:
    return {"Authorization": f"Bearer {app.config['TEST_ACCESS_TOKEN']}"}


def test_monday_dashboard_composes_schedule_targets_and_achievement(app: Flask) -> None:
    response = app.test_client().get("/api/v1/public/dashboard?date=2026-07-13")

    assert response.status_code == 200
    dashboard = response.get_json()
    assert dashboard["date"] == "2026-07-13"
    assert dashboard["profile"]["display_name"] == "Brandan Burgess"
    assert dashboard["scheduled_day"]["name"] == "Upper A — Incline + Back"
    assert dashboard["scheduled_day"]["items"][1]["exercise"]["slug"] == (
        "incline_barbell_bench_press"
    )
    targets = {target["slug"]: target for target in dashboard["muscle_targets"]}
    assert targets["upper_chest"]["role"] == "primary"
    assert targets["upper_chest"]["intensity"] == 1.0
    assert targets["mid_chest"]["role"] == "secondary"
    assert targets["lats"]["role"] == "primary"
    assert targets["upper_back"]["role"] == "primary"
    assert targets["side_delts"]["role"] == "primary"
    assert targets["biceps"]["role"] == "primary"
    assert targets["triceps"]["role"] == "primary"
    assert targets["front_delts"]["role"] == "secondary"
    assert dashboard["water"] is None
    assert dashboard["latest_achievements"][0]["title"] == "New incline record"


def test_saturday_uses_optional_conditioning_day(app: Flask) -> None:
    response = app.test_client().get("/api/v1/public/dashboard?date=2026-07-18")
    day = response.get_json()["scheduled_day"]

    assert day["is_optional"] is True
    assert day["name"] == "Optional — Condition or Specialize"
    assert day["items"][1]["exercise"]["slug"] == "stationary_bike_intervals"


def test_owner_sees_private_active_session_while_public_does_not(app: Flask) -> None:
    with app.app_context(), Session(get_engine()) as session, session.begin():
        session.add(
            WorkoutSession(
                split_day_id=None,
                session_date_local=MONDAY,
                started_at=datetime(2026, 7, 13, 17, 0, tzinfo=UTC),
                completed_at=None,
                status=SessionStatus.IN_PROGRESS,
                title="Private workout",
                public_visibility=PublicVisibility.PRIVATE,
                perceived_effort=None,
                notes_private="owner-only note",
                notes_public=None,
                deleted_at=None,
            )
        )

    client = app.test_client()
    public = client.get("/api/v1/public/dashboard?date=2026-07-13").get_json()
    owner = client.get("/api/v1/public/dashboard?date=2026-07-13", headers=_auth(app)).get_json()

    assert public["active_session"] is None
    assert owner["active_session"]["title"] == "Private workout"
    assert owner["active_session"]["notes_private"] == "owner-only note"


def test_water_visibility_and_owner_override(app: Flask) -> None:
    with app.app_context(), Session(get_engine()) as session, session.begin():
        session.add(
            WaterLog(
                occurred_at=datetime(2026, 7, 13, 16, 0, tzinfo=UTC),
                local_date=MONDAY,
                amount_ml=500,
                source=WaterSource.CUSTOM,
                note="private",
            )
        )

    client = app.test_client()
    public = client.get("/api/v1/public/dashboard?date=2026-07-13").get_json()
    owner = client.get("/api/v1/public/dashboard?date=2026-07-13", headers=_auth(app)).get_json()
    assert public["water"] is None
    assert owner["water"]["total_ml"] == 500

    with app.app_context(), Session(get_engine()) as session, session.begin():
        visibility = session.scalar(select(VisibilitySettings))
        assert visibility is not None
        visibility.show_water = True
    visible = client.get("/api/v1/public/dashboard?date=2026-07-13").get_json()
    assert visible["water"]["total_ml"] == 500


def test_rest_day_and_invalid_date_are_handled(app: Flask) -> None:
    rest = app.test_client().get("/api/v1/public/dashboard?date=2026-07-15")
    assert rest.status_code == 200
    assert rest.get_json()["scheduled_day"] is None
    assert rest.get_json()["muscle_targets"] == []

    invalid = app.test_client().get("/api/v1/public/dashboard?date=invalid")
    assert invalid.status_code == 400
    assert "date" in invalid.get_json()["error"]["field_errors"]
