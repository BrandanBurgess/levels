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
    Base,
    PublicVisibility,
    ScheduleState,
    SessionExercise,
    SessionStatus,
    User,
    WorkoutSession,
)
from levels_api.seed import seed_session

JWT_SECRET = "tests-only-jwt-signing-key-32-characters-long"


@pytest.fixture
def app(tmp_path: Path) -> Iterator[Flask]:
    application = create_app(
        Settings.for_testing(
            f"sqlite+pysqlite:///{tmp_path / 'splits.db'}",
            admin_username="brandan",
            admin_password_hash="$argon2id$unused-in-route-tests",
            jwt_secret_key=JWT_SECRET,
        )
    )
    with application.app_context():
        engine = get_engine()
        Base.metadata.create_all(engine)
        with Session(engine) as session, session.begin():
            seeded = seed_session(session)
            user = session.get(User, seeded.user_id)
            assert user is not None
            token, _ = create_access_token(user)
        application.config["TEST_ACCESS_TOKEN"] = token
    yield application
    with application.app_context():
        get_engine().dispose()


def _auth(app: Flask) -> dict[str, str]:
    return {"Authorization": f"Bearer {app.config['TEST_ACCESS_TOKEN']}"}


def _write() -> dict[str, object]:
    return {
        "name": "Two Day Test",
        "slug": "two-day-test",
        "description": "A custom plan",
        "days": [
            {
                "name": "Push Test",
                "day_type": "upper",
                "sequence": 1,
                "is_optional": False,
                "items": [
                    {
                        "exercise_id": "push_up",
                        "sequence": 1,
                        "item_type": "main",
                        "sets": 3,
                        "rep_min": 8,
                        "rep_max": 12,
                        "rest_seconds": 90,
                        "target_rir": 2,
                        "optional": False,
                        "alternative_exercise_ids": ["flat_dumbbell_bench_press"],
                    },
                    {
                        "exercise_id": "rope_triceps_pressdown",
                        "sequence": 2,
                        "item_type": "accessory",
                        "sets": 2,
                        "optional": False,
                        "alternative_exercise_ids": [],
                    },
                ],
            }
        ],
    }


def _write_from_detail(
    detail: dict[str, object], days: list[dict[str, object]]
) -> dict[str, object]:
    return {
        "name": detail["name"],
        "slug": detail["slug"],
        "description": detail["description"],
        "days": [
            {
                "id": day["id"],
                "name": day["name"],
                "day_type": day["day_type"],
                "sequence": index,
                "is_optional": day["is_optional"],
                "items": [
                    {
                        "id": item["id"],
                        "exercise_id": item["exercise"]["id"],
                        "sequence": item_index,
                        "item_type": item["item_type"],
                        "sets": item["sets"],
                        "rep_min": item["rep_min"],
                        "rep_max": item["rep_max"],
                        "duration_seconds": item["duration_seconds"],
                        "distance_meters": item["distance_meters"],
                        "rounds_target": item["rounds_target"],
                        "rest_seconds": item["rest_seconds"],
                        "target_rir": item["target_rir"],
                        "optional": item["optional"],
                        "alternative_exercise_ids": [
                            alternative["id"] for alternative in item["alternatives"]
                        ],
                    }
                    for item_index, item in enumerate(day["items"], start=1)
                ],
            }
            for index, day in enumerate(days, start=1)
        ],
    }


def test_private_split_list_and_detail_are_ordered_and_complete(app: Flask) -> None:
    client = app.test_client()
    assert client.get("/api/v1/splits").status_code == 401
    splits = client.get("/api/v1/splits", headers=_auth(app))

    assert splits.status_code == 200
    payload = splits.get_json()
    assert [split["slug"] for split in payload] == [
        "brandan-athletic-upper-lower",
        "push-pull-legs",
    ]
    assert payload[0]["is_active"] is True
    split_id = payload[0]["id"]
    detail = client.get(f"/api/v1/splits/{split_id}", headers=_auth(app)).get_json()
    assert [day["sequence"] for day in detail["days"]] == [1, 2, 3, 4, 5]
    assert detail["days"][0]["items"][1]["alternatives"]


def test_split_writes_require_authentication(app: Flask) -> None:
    client = app.test_client()
    active_id = client.get("/api/v1/splits", headers=_auth(app)).get_json()[0]["id"]

    assert client.post("/api/v1/splits", json=_write()).status_code == 401
    assert client.patch(f"/api/v1/splits/{active_id}", json=_write()).status_code == 401
    assert client.post(f"/api/v1/splits/{active_id}/activate").status_code == 401
    assert client.delete(f"/api/v1/splits/{active_id}").status_code == 401


def test_owner_create_and_reorder_preserves_day_and_item_ids(app: Flask) -> None:
    client = app.test_client()
    created = client.post("/api/v1/splits", json=_write(), headers=_auth(app))

    assert created.status_code == 201
    split = created.get_json()
    day = split["days"][0]
    original_item_ids = [item["id"] for item in day["items"]]
    write = _write()
    write_day = write["days"][0]  # type: ignore[index]
    write_day["id"] = day["id"]  # type: ignore[index]
    write_items = write_day["items"]  # type: ignore[index]
    for item, item_id in zip(write_items, original_item_ids, strict=True):
        item["id"] = item_id
    write_items[0]["sequence"] = 2
    write_items[1]["sequence"] = 1

    updated = client.patch(f"/api/v1/splits/{split['id']}", json=write, headers=_auth(app))

    assert updated.status_code == 200
    updated_items = updated.get_json()["days"][0]["items"]
    assert [item["exercise"]["id"] for item in updated_items] == [
        "rope_triceps_pressdown",
        "push_up",
    ]
    assert {item["id"] for item in updated_items} == set(original_item_ids)
    archived = client.delete(f"/api/v1/splits/{split['id']}", headers=_auth(app))
    assert archived.status_code == 204
    assert all(
        candidate["id"] != split["id"]
        for candidate in client.get("/api/v1/splits", headers=_auth(app)).get_json()
    )


def test_activation_updates_single_active_split_and_profile_settings(app: Flask) -> None:
    client = app.test_client()
    created = client.post("/api/v1/splits", json=_write(), headers=_auth(app)).get_json()

    activated = client.post(f"/api/v1/splits/{created['id']}/activate", headers=_auth(app))

    assert activated.status_code == 200
    assert activated.get_json()["is_active"] is True
    assert (
        sum(
            split["is_active"]
            for split in client.get("/api/v1/splits", headers=_auth(app)).get_json()
        )
        == 1
    )
    assert (
        client.get("/api/v1/settings", headers=_auth(app)).get_json()["active_split_id"]
        == (created["id"])
    )
    with app.app_context(), Session(get_engine()) as session:
        schedule = session.scalar(select(ScheduleState))
        assert schedule is not None
        assert schedule.active_split_id == created["id"]
        assert schedule.cursor_split_day_id == created["days"][0]["id"]
        assert schedule.version == 1
    blocked = client.delete(f"/api/v1/splits/{created['id']}", headers=_auth(app))
    assert blocked.status_code == 409
    assert blocked.get_json()["error"]["code"] == "ACTIVE_SPLIT"


def test_removing_split_day_preserves_completed_session_payload(app: Flask) -> None:
    client = app.test_client()
    detail = client.get("/api/v1/splits", headers=_auth(app)).get_json()[0]
    retired_day = detail["days"][0]
    source = retired_day["items"][0]
    with app.app_context(), Session(get_engine()) as session, session.begin():
        user = session.scalar(
            select(User).where(User.email_normalized == "seed-owner@levels.local")
        )
        assert user is not None
        workout = WorkoutSession(
            user_id=user.id,
            split_day_id=retired_day["id"],
            session_date_local=date(2026, 7, 13),
            started_at=datetime(2026, 7, 13, 18, tzinfo=UTC),
            completed_at=datetime(2026, 7, 13, 19, tzinfo=UTC),
            status=SessionStatus.COMPLETED,
            title=retired_day["name"],
            public_visibility=PublicVisibility.PRIVATE,
        )
        workout.exercises.append(
            SessionExercise(
                exercise_id=source["exercise"]["id"],
                source_template_item_id=source["id"],
                sequence=0,
                planned_sets=source["sets"],
                item_type=source["item_type"],
                display_name_snapshot=source["exercise"]["name"],
                variation_group_snapshot=source["exercise"]["variation_group"],
                rep_min_snapshot=source["rep_min"],
                rep_max_snapshot=source["rep_max"],
                rest_seconds_snapshot=source["rest_seconds"],
                optional_snapshot=source["optional"],
            )
        )
        session.add(workout)
        session.flush()
        workout_id = workout.id

    before = client.get(f"/api/v1/sessions/{workout_id}", headers=_auth(app)).get_json()
    updated = client.patch(
        f"/api/v1/splits/{detail['id']}",
        headers=_auth(app),
        json=_write_from_detail(detail, detail["days"][1:]),
    )
    assert updated.status_code == 200, updated.get_json()
    after = client.get(f"/api/v1/sessions/{workout_id}", headers=_auth(app)).get_json()
    assert after == before


def test_template_validation_rejects_unknown_or_ambiguous_content(app: Flask) -> None:
    client = app.test_client()
    unknown = _write()
    unknown["days"][0]["items"][0]["exercise_id"] = "not-real"  # type: ignore[index]
    duplicate = _write()
    duplicate["days"][0]["items"][1]["sequence"] = 1  # type: ignore[index]

    assert client.post("/api/v1/splits", json=unknown, headers=_auth(app)).status_code == 400
    assert client.post("/api/v1/splits", json=duplicate, headers=_auth(app)).status_code == 400
    assert client.get("/api/v1/splits/not-real", headers=_auth(app)).status_code == 404
