from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from flask import Flask
from sqlalchemy.orm import Session

from levels_api import Settings, create_app
from levels_api.auth.service import create_access_token
from levels_api.database import get_engine
from levels_api.models import Base
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
            seed_session(session)
        token, _ = create_access_token("brandan")
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


def test_public_split_list_and_detail_are_ordered_and_complete(app: Flask) -> None:
    client = app.test_client()
    splits = client.get("/api/v1/splits")

    assert splits.status_code == 200
    payload = splits.get_json()
    assert [split["slug"] for split in payload] == [
        "brandan-athletic-upper-lower",
        "push-pull-legs",
    ]
    assert payload[0]["is_active"] is True
    split_id = payload[0]["id"]
    detail = client.get(f"/api/v1/splits/{split_id}").get_json()
    assert [day["sequence"] for day in detail["days"]] == [1, 2, 3, 4, 5]
    assert detail["days"][0]["items"][1]["alternatives"]


def test_split_writes_require_authentication(app: Flask) -> None:
    client = app.test_client()
    active_id = client.get("/api/v1/splits").get_json()[0]["id"]

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
        candidate["id"] != split["id"] for candidate in client.get("/api/v1/splits").get_json()
    )


def test_activation_updates_single_active_split_and_profile_settings(app: Flask) -> None:
    client = app.test_client()
    created = client.post("/api/v1/splits", json=_write(), headers=_auth(app)).get_json()

    activated = client.post(f"/api/v1/splits/{created['id']}/activate", headers=_auth(app))

    assert activated.status_code == 200
    assert activated.get_json()["is_active"] is True
    assert sum(split["is_active"] for split in client.get("/api/v1/splits").get_json()) == 1
    assert (
        client.get("/api/v1/settings", headers=_auth(app)).get_json()["active_split_id"]
        == (created["id"])
    )
    blocked = client.delete(f"/api/v1/splits/{created['id']}", headers=_auth(app))
    assert blocked.status_code == 409
    assert blocked.get_json()["error"]["code"] == "ACTIVE_SPLIT"


def test_template_validation_rejects_unknown_or_ambiguous_content(app: Flask) -> None:
    client = app.test_client()
    unknown = _write()
    unknown["days"][0]["items"][0]["exercise_id"] = "not-real"  # type: ignore[index]
    duplicate = _write()
    duplicate["days"][0]["items"][1]["sequence"] = 1  # type: ignore[index]

    assert client.post("/api/v1/splits", json=unknown, headers=_auth(app)).status_code == 400
    assert client.post("/api/v1/splits", json=duplicate, headers=_auth(app)).status_code == 400
    assert client.get("/api/v1/splits/not-real").status_code == 404
