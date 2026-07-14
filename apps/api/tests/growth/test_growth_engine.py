from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from flask import Flask
from sqlalchemy.orm import Session

from levels_api import Settings, create_app
from levels_api.auth.service import create_access_token
from levels_api.database import get_engine
from levels_api.models import Base, ReadinessLog
from levels_api.seed import seed_session

JWT_SECRET = "tests-only-jwt-signing-key-32-characters-long"
EXERCISE_ID = "incline_barbell_bench_press"


@pytest.fixture
def app(tmp_path: Path) -> Iterator[Flask]:
    application = create_app(
        Settings.for_testing(
            f"sqlite+pysqlite:///{tmp_path / 'growth.db'}",
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
        token, _ = create_access_token("brandan")
        application.config["TEST_ACCESS_TOKEN"] = token
    yield application
    with application.app_context():
        get_engine().dispose()


def _auth(app: Flask) -> dict[str, str]:
    return {"Authorization": f"Bearer {app.config['TEST_ACCESS_TOKEN']}"}


def _upper_day_id(app: Flask) -> str:
    return app.test_client().get("/api/v1/splits").get_json()[0]["days"][0]["id"]


def _completed_session(
    app: Flask,
    local_date: str,
    reps: int,
    *,
    rir: float = 2,
    form: int = 4,
    pain: bool = False,
    visibility: str = "full",
) -> str:
    client = app.test_client()
    workout = client.post(
        "/api/v1/sessions",
        json={"title": f"Evidence {local_date}", "date": local_date},
        headers=_auth(app),
    ).get_json()
    item = client.post(
        f"/api/v1/sessions/{workout['id']}/exercises",
        json={"exercise_id": EXERCISE_ID},
        headers=_auth(app),
    ).get_json()
    response = client.post(
        f"/api/v1/sessions/{workout['id']}/sets",
        json={
            "session_exercise_id": item["id"],
            "set_type": "working",
            "load_kg": 60,
            "reps": reps,
            "rir": rir,
            "form_quality": form,
            "pain_flag": pain,
        },
        headers=_auth(app),
    )
    assert response.status_code == 201
    completed = client.patch(
        f"/api/v1/sessions/{workout['id']}",
        json={"status": "completed", "public_visibility": visibility},
        headers=_auth(app),
    )
    assert completed.status_code == 200
    return workout["id"]


def _suggestion(app: Flask, *, owner: bool = True) -> dict[str, object]:
    headers = _auth(app) if owner else None
    response = app.test_client().get(
        f"/api/v1/growth/suggestions?date=2026-07-13&split_day_id={_upper_day_id(app)}",
        headers=headers,
    )
    assert response.status_code == 200
    return next(item for item in response.get_json() if item["exercise_id"] == EXERCISE_ID)


def test_fewer_than_two_comparable_sessions_is_insufficient(app: Flask) -> None:
    first = _suggestion(app)
    assert first["suggestion_type"] == "insufficient_data"
    assert first["confidence"] == "insufficient"
    assert first["source_session_ids"] == []

    session_id = _completed_session(app, "2026-07-10", 8)
    one = _suggestion(app)
    assert one["suggestion_type"] == "insufficient_data"
    assert one["source_session_ids"] == [session_id]


def test_top_of_range_allows_only_smallest_configured_increment(app: Flask) -> None:
    older = _completed_session(app, "2026-07-09", 8)
    latest = _completed_session(app, "2026-07-10", 8)

    suggestion = _suggestion(app)
    assert suggestion["suggestion_type"] == "increase_load"
    assert suggestion["suggested_delta"] == pytest.approx(1.133981)
    assert suggestion["delta_unit"] == "kg"
    assert suggestion["source_session_ids"] == [latest, older]
    assert "smallest configured load increment" in " ".join(suggestion["explanation"])


@pytest.mark.parametrize(
    ("older_reps", "latest_reps", "expected"),
    [(6, 7, "repeat_load"), (6, 6, "add_rep")],
)
def test_rep_progression_stays_conservative(
    app: Flask, older_reps: int, latest_reps: int, expected: str
) -> None:
    _completed_session(app, "2026-07-09", older_reps)
    _completed_session(app, "2026-07-10", latest_reps)
    suggestion = _suggestion(app)
    assert suggestion["suggestion_type"] == expected
    assert "10%" not in " ".join(suggestion["explanation"])
    assert "max single" not in " ".join(suggestion["explanation"])


def test_pain_prevents_overload(app: Flask) -> None:
    _completed_session(app, "2026-07-09", 8)
    _completed_session(app, "2026-07-10", 8, pain=True)
    suggestion = _suggestion(app)
    assert suggestion["suggestion_type"] == "no_progression"
    assert suggestion["suggested_delta"] is None
    assert "Pain" in suggestion["explanation"][0]


def test_two_declines_and_low_readiness_maintain_without_overload(app: Flask) -> None:
    _completed_session(app, "2026-07-08", 8)
    _completed_session(app, "2026-07-09", 7)
    _completed_session(app, "2026-07-10", 6)
    suggestion = _suggestion(app)
    assert suggestion["suggestion_type"] == "maintain"
    assert "declined" in suggestion["explanation"][0]

    with app.app_context(), Session(get_engine()) as session, session.begin():
        session.add(
            ReadinessLog(
                local_date=date(2026, 7, 13),
                energy=2,
                soreness=4,
                sleep_quality=2,
                pain_flag=False,
            )
        )
    readiness = _suggestion(app)
    assert readiness["suggestion_type"] == "maintain"
    assert "readiness" in readiness["explanation"][0]


def test_public_growth_uses_only_full_public_evidence(app: Flask) -> None:
    _completed_session(app, "2026-07-09", 8, visibility="private")
    _completed_session(app, "2026-07-10", 8, visibility="private")
    public = _suggestion(app, owner=False)
    assert public["suggestion_type"] == "insufficient_data"
    assert public["source_session_ids"] == []
