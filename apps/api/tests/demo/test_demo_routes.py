from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from levels_api import Settings, create_app
from levels_api.database import get_engine
from levels_api.models import Base, SessionStatus, User, UserRole, UserStatus, WorkoutSession
from levels_api.seed import seed_demo_session


def test_demo_is_anonymous_fictional_get_only_and_tenant_bound(tmp_path: Path) -> None:
    app = create_app(Settings.for_testing(f"sqlite+pysqlite:///{tmp_path / 'demo.db'}"))
    with app.app_context():
        Base.metadata.create_all(get_engine())
        with Session(get_engine()) as session, session.begin():
            seed_demo_session(session)
            real_user = User(
                id="real-user",
                email_normalized="private@example.com",
                password_hash="$argon2id$fixture",
                status=UserStatus.ACTIVE,
                role=UserRole.MEMBER,
                token_version=0,
                is_demo=False,
            )
            session.add(real_user)
            session.flush()
            session.add(
                WorkoutSession(
                    user_id=real_user.id,
                    version=0,
                    session_date_local=date(2026, 7, 15),
                    started_at=datetime(2026, 7, 15, 12, tzinfo=UTC),
                    completed_at=datetime(2026, 7, 15, 13, tzinfo=UTC),
                    status=SessionStatus.COMPLETED,
                    title="PRIVATE SESSION MUST NOT LEAK",
                )
            )

    client = app.test_client()
    response = client.get("/api/v1/demo/bootstrap")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["mode"] == "demo"
    assert payload["profile"]["display_name"] == "Alex Rivers"
    assert payload["today"]["profile"] == payload["profile"]
    assert payload["splits"]
    assert payload["exercises"]
    assert payload["journal_samples"]
    assert payload["progress"]["completed_sessions"] == 2
    serialized = response.get_data(as_text=True)
    assert "private@example.com" not in serialized
    assert "PRIVATE SESSION MUST NOT LEAK" not in serialized
    assert "password" not in serialized.casefold()

    assert client.post("/api/v1/demo/bootstrap", json={}).status_code == 405
    with app.app_context():
        get_engine().dispose()
