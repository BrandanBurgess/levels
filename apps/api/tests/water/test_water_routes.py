from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from flask import Flask
from sqlalchemy import select
from sqlalchemy.orm import Session

from levels_api import Settings, create_app
from levels_api.auth.service import create_access_token
from levels_api.database import get_engine
from levels_api.models import Base, VisibilitySettings, WaterLog
from levels_api.seed import seed_session

JWT_SECRET = "tests-only-jwt-signing-key-32-characters-long"


@pytest.fixture
def app(tmp_path: Path) -> Iterator[Flask]:
    application = create_app(
        Settings.for_testing(
            f"sqlite+pysqlite:///{tmp_path / 'water.db'}",
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


def test_public_water_is_hidden_by_default_but_owner_can_read(app: Flask) -> None:
    client = app.test_client()
    route = "/api/v1/water/today?date=2026-07-13"
    assert client.get(route).status_code == 404

    owner = client.get(route, headers=_auth(app))
    assert owner.status_code == 200
    assert owner.get_json()["total_ml"] == 0


def test_quick_add_custom_timezones_and_idempotency(app: Flask) -> None:
    client = app.test_client()
    route = "/api/v1/water/today"
    headers = {**_auth(app), "Idempotency-Key": "water-add-1"}
    payload = {
        "amount_ml": 500,
        "source": "quick_add",
        "occurred_at": "2026-07-14T02:00:00Z",
    }

    first = client.post(route, headers=headers, json=payload)
    replay = client.post(route, headers=headers, json=payload)
    custom = client.post(
        route,
        headers={**_auth(app), "Idempotency-Key": "water-add-2"},
        json={
            "amount_ml": 375,
            "source": "custom",
            "note": "after training",
            "occurred_at": "2026-07-13T20:00:00-04:00",
        },
    )

    assert first.status_code == 201
    assert replay.status_code == 201
    assert custom.status_code == 201
    assert custom.get_json()["local_date"] == "2026-07-13"
    assert custom.get_json()["total_ml"] == 875
    with app.app_context(), Session(get_engine()) as session:
        assert len(list(session.scalars(select(WaterLog)))) == 2


def test_undo_removes_latest_entry_for_requested_local_date(app: Flask) -> None:
    client = app.test_client()
    for key, amount, instant in (
        ("undo-1", 250, "2026-07-13T18:00:00-04:00"),
        ("undo-2", 750, "2026-07-13T19:00:00-04:00"),
    ):
        client.post(
            "/api/v1/water/today",
            headers={**_auth(app), "Idempotency-Key": key},
            json={"amount_ml": amount, "occurred_at": instant},
        )

    undone = client.post("/api/v1/water/today/undo?date=2026-07-13", headers=_auth(app))
    assert undone.status_code == 200
    assert undone.get_json()["total_ml"] == 250
    assert [entry["amount_ml"] for entry in undone.get_json()["entries"]] == [250]


def test_undo_uses_profile_local_date_without_nesting_transactions(app: Flask) -> None:
    client = app.test_client()
    added = client.post(
        "/api/v1/water/today",
        headers={**_auth(app), "Idempotency-Key": "undo-current-day"},
        json={"amount_ml": 500},
    )
    assert added.status_code == 201

    undone = client.post("/api/v1/water/today/undo", headers=_auth(app))
    assert undone.status_code == 200
    assert undone.get_json()["total_ml"] == 0


def test_undo_empty_day_returns_not_found(app: Flask) -> None:
    response = app.test_client().post(
        "/api/v1/water/today/undo?date=2020-01-01", headers=_auth(app)
    )
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "WATER_ENTRY_NOT_FOUND"


def test_public_water_can_be_enabled_without_private_entry_fields(app: Flask) -> None:
    client = app.test_client()
    client.post(
        "/api/v1/water/today",
        headers=_auth(app),
        json={"amount_ml": 500, "occurred_at": "2026-07-13T12:00:00-04:00"},
    )
    with app.app_context(), Session(get_engine()) as session, session.begin():
        visibility = session.scalar(select(VisibilitySettings))
        assert visibility is not None
        visibility.show_water = True

    public = client.get("/api/v1/water/today?date=2026-07-13")
    assert public.status_code == 200
    assert public.get_json()["total_ml"] == 500
    assert set(public.get_json()["entries"][0]) == {"id", "amount_ml", "occurred_at"}


@pytest.mark.parametrize(
    "payload",
    [
        {"amount_ml": 0},
        {"amount_ml": 5001},
        {"amount_ml": 250, "source": "unknown"},
        {"amount_ml": 250, "occurred_at": "2026-07-13T12:00:00"},
        {"amount_ml": 250, "unexpected": True},
    ],
)
def test_invalid_water_writes_are_rejected_without_mutation(
    app: Flask, payload: dict[str, object]
) -> None:
    response = app.test_client().post("/api/v1/water/today", headers=_auth(app), json=payload)
    assert response.status_code == 400
    with app.app_context(), Session(get_engine()) as session:
        assert session.scalar(select(WaterLog.id)) is None


def test_invalid_date_and_unauthenticated_writes_are_rejected(app: Flask) -> None:
    client = app.test_client()
    assert client.post("/api/v1/water/today", json={"amount_ml": 250}).status_code == 401
    response = client.get("/api/v1/water/today?date=not-a-date", headers=_auth(app))
    assert response.status_code == 400
    assert "date" in response.get_json()["error"]["field_errors"]
