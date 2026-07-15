from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from flask import Flask
from sqlalchemy.orm import Session

from levels_api import Settings, create_app
from levels_api.auth.service import create_access_token
from levels_api.database import get_engine
from levels_api.models import Base, PublicVisibility, SessionStatus, User, WorkoutSession
from levels_api.seed import seed_session

JWT_SECRET = "tests-only-jwt-signing-key-32-characters-long"


@pytest.fixture
def app(tmp_path: Path) -> Iterator[Flask]:
    application = create_app(
        Settings.for_testing(
            f"sqlite+pysqlite:///{tmp_path / 'export.db'}",
            admin_username="brandan",
            admin_password_hash="$argon2id$never-export-this-password-hash",
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
            application.config["TEST_USER_ID"] = user.id
        application.config["TEST_ACCESS_TOKEN"] = token
    yield application
    with application.app_context():
        get_engine().dispose()


def _auth(app: Flask) -> dict[str, str]:
    return {"Authorization": f"Bearer {app.config['TEST_ACCESS_TOKEN']}"}


def _session_with_formula_notes(app: Flask) -> str:
    with app.app_context(), Session(get_engine()) as db, db.begin():
        workout = WorkoutSession(
            user_id=str(app.config["TEST_USER_ID"]),
            version=0,
            session_date_local=date(2026, 7, 13),
            started_at=datetime.now(UTC),
            status=SessionStatus.IN_PROGRESS,
            title="@unsafe-title",
            public_visibility=PublicVisibility.PRIVATE,
            notes_private="=2+2",
            notes_public="+SUM(1,1)",
        )
        db.add(workout)
        db.flush()
        return workout.id


def test_export_is_owner_only_and_validates_format(app: Flask) -> None:
    client = app.test_client()
    assert client.get("/api/v1/export?format=json").status_code == 401
    assert client.get("/api/v1/export?format=csv").status_code == 401
    invalid = client.get("/api/v1/export?format=xml", headers=_auth(app))
    assert invalid.status_code == 400
    assert invalid.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_json_export_is_complete_and_excludes_environment_secrets(app: Flask) -> None:
    session_id = _session_with_formula_notes(app)
    response = app.test_client().get("/api/v1/export?format=json", headers=_auth(app))

    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert "attachment" in response.headers["Content-Disposition"]
    payload = response.get_json()
    assert payload["schema_version"] == "0.1.0"
    assert {"profiles", "workout_sessions", "set_logs", "personal_records"} <= set(
        payload["tables"]
    )
    exported = next(row for row in payload["tables"]["workout_sessions"] if row["id"] == session_id)
    assert exported["notes_private"] == "=2+2"
    body = response.get_data(as_text=True)
    assert "never-export-this-password-hash" not in body
    assert JWT_SECRET not in body


def test_csv_export_escapes_spreadsheet_formula_prefixes(app: Flask) -> None:
    _session_with_formula_notes(app)
    with app.app_context(), Session(get_engine()) as db, db.begin():
        db.add(
            WorkoutSession(
                user_id=str(app.config["TEST_USER_ID"]),
                version=0,
                session_date_local=date(2026, 7, 14),
                started_at=datetime.now(UTC),
                status=SessionStatus.IN_PROGRESS,
                title="-10+20",
                public_visibility=PublicVisibility.PRIVATE,
                notes_private="\t=unsafe",
                notes_public="\r=unsafe",
            )
        )
    client = app.test_client()
    response = client.get("/api/v1/export?format=csv", headers=_auth(app))

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert response.get_data(as_text=True).startswith("table,row,column,value\r\n")
    body = response.get_data(as_text=True)
    assert "'=2+2" in body
    assert "'+SUM(1,1)" in body
    assert "'@unsafe-title" in body
    assert "'-10+20" in body
    assert "'\t=unsafe" in body
    assert "'\r=unsafe" in body
