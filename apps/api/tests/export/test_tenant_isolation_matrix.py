from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from flask import Flask
from sqlalchemy.orm import Session

from levels_api import Settings, create_app
from levels_api.auth.service import create_access_token
from levels_api.database import get_engine
from levels_api.models import (
    Base,
    PersonalRecord,
    RecordType,
    User,
    UserRole,
    UserStatus,
)
from levels_api.seed import seed_user_starter


@pytest.fixture
def tenant_app(tmp_path: Path) -> Iterator[Flask]:
    app = create_app(Settings.for_testing(f"sqlite+pysqlite:///{tmp_path / 'tenants.db'}"))
    with app.app_context():
        engine = get_engine()
        Base.metadata.create_all(engine)
        with Session(engine) as session, session.begin():
            first = User(
                email_normalized="first@example.test",
                password_hash="$argon2id$first-secret-marker",
                status=UserStatus.ACTIVE,
                role=UserRole.MEMBER,
                token_version=0,
                is_demo=False,
            )
            second = User(
                email_normalized="second@example.test",
                password_hash="$argon2id$second-secret-marker",
                status=UserStatus.ACTIVE,
                role=UserRole.MEMBER,
                token_version=0,
                is_demo=False,
            )
            session.add_all([first, second])
            session.flush()
            seed_user_starter(session, first, display_name="First Tenant")
            seed_user_starter(session, second, display_name="Second Tenant")
            first_token, _ = create_access_token(first)
            second_token, _ = create_access_token(second)
            app.config.update(
                FIRST_ID=first.id,
                SECOND_ID=second.id,
                FIRST_TOKEN=first_token,
                SECOND_TOKEN=second_token,
            )
    yield app
    with app.app_context():
        get_engine().dispose()


def _auth(app: Flask, tenant: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {app.config[f'{tenant}_TOKEN']}"}


def _exercise_write(name: str, slug: str) -> dict[str, object]:
    return {
        "name": name,
        "slug": slug,
        "aliases": [],
        "variation_group": slug,
        "movement_pattern": "horizontal_push",
        "equipment": "cable",
        "measurement_type": "load_reps",
        "compound": False,
        "unilateral": False,
        "default_rep_min": 8,
        "default_rep_max": 12,
        "default_rest_seconds": 60,
        "automatic_progression_enabled": True,
        "muscle_targets": [{"slug": "upper_chest", "role": "primary", "intensity": 1}],
    }


def test_two_user_isolation_matrix(tenant_app: Flask) -> None:
    client = tenant_app.test_client()
    first_auth = _auth(tenant_app, "FIRST")
    second_auth = _auth(tenant_app, "SECOND")

    first_profile = client.get("/api/v1/me/profile", headers=first_auth).get_json()
    second_profile = client.get("/api/v1/me/profile", headers=second_auth).get_json()
    assert first_profile["display_name"] == "First Tenant"
    assert second_profile["display_name"] == "Second Tenant"

    first_splits = client.get("/api/v1/splits", headers=first_auth).get_json()
    second_splits = client.get("/api/v1/splits", headers=second_auth).get_json()
    second_split_id = second_splits[0]["id"]
    second_day_id = second_splits[0]["days"][0]["id"]
    assert {split["id"] for split in first_splits}.isdisjoint(
        split["id"] for split in second_splits
    )
    assert client.get(f"/api/v1/splits/{second_split_id}", headers=first_auth).status_code == 404
    assert (
        client.patch(
            "/api/v1/settings", headers=first_auth, json={"active_split_id": second_split_id}
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/growth/suggestions?split_day_id={second_day_id}", headers=first_auth
        ).status_code
        == 404
    )

    first_custom = client.post(
        "/api/v1/exercises",
        headers=first_auth,
        json=_exercise_write("First Private Press", "private_press"),
    ).get_json()
    second_custom = client.post(
        "/api/v1/exercises",
        headers=second_auth,
        json=_exercise_write("Second Private Press", "private_press"),
    ).get_json()
    assert first_custom["id"] != second_custom["id"]
    assert (
        client.get(f"/api/v1/exercises/{second_custom['id']}", headers=first_auth).status_code
        == 404
    )
    assert {
        exercise["id"]
        for exercise in client.get("/api/v1/exercises?scope=mine", headers=first_auth).get_json()
    } == {first_custom["id"]}
    assert (
        client.patch(
            "/api/v1/exercises/push_up",
            headers=first_auth,
            json=_exercise_write("Cannot Edit Global", "cannot_edit_global"),
        ).status_code
        == 403
    )

    client.post(
        "/api/v1/water/today",
        headers={**first_auth, "Idempotency-Key": "shared-key"},
        json={"amount_ml": 250, "occurred_at": "2026-07-13T12:00:00Z"},
    )
    client.post(
        "/api/v1/water/today",
        headers={**second_auth, "Idempotency-Key": "shared-key"},
        json={"amount_ml": 750, "occurred_at": "2026-07-13T12:00:00Z"},
    )
    assert (
        client.get("/api/v1/water/today?date=2026-07-13", headers=first_auth).get_json()["total_ml"]
        == 250
    )
    assert (
        client.get("/api/v1/water/today?date=2026-07-13", headers=second_auth).get_json()[
            "total_ml"
        ]
        == 750
    )

    with tenant_app.app_context(), Session(get_engine()) as session, session.begin():
        session.add_all(
            [
                PersonalRecord(
                    user_id=str(tenant_app.config["FIRST_ID"]),
                    exercise_id="push_up",
                    record_type=RecordType.REPS_AT_LOAD,
                    value_numeric=Decimal("11"),
                    unit="reps",
                    achieved_at=datetime.now(UTC),
                    is_current=True,
                ),
                PersonalRecord(
                    user_id=str(tenant_app.config["SECOND_ID"]),
                    exercise_id="push_up",
                    record_type=RecordType.REPS_AT_LOAD,
                    value_numeric=Decimal("22"),
                    unit="reps",
                    achieved_at=datetime.now(UTC),
                    is_current=True,
                ),
            ]
        )
    assert {
        item["value_numeric"]
        for item in client.get("/api/v1/records", headers=first_auth).get_json()
    } == {11}

    export = client.get("/api/v1/export?format=json", headers=first_auth)
    body = export.get_data(as_text=True)
    assert export.status_code == 200
    assert str(tenant_app.config["SECOND_ID"]) not in body
    assert "Second Tenant" not in body
    assert "second-secret-marker" not in body
    assert "first-secret-marker" not in body
    assert "users" not in export.get_json()["tables"]
