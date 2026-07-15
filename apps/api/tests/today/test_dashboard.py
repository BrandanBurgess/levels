from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from flask import Flask
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from levels_api import Settings, create_app
from levels_api.auth.service import create_access_token
from levels_api.database import get_engine
from levels_api.models import (
    Base,
    DailyPlanOverride,
    ScheduleState,
    Split,
    SplitDay,
    User,
    UserRole,
    UserStatus,
    WorkoutTemplateItem,
)
from levels_api.seed import seed_user_starter

JWT_SECRET = "tests-only-jwt-signing-key-32-characters-long"
MONDAY = "2026-07-13"
TUESDAY = "2026-07-14"


@pytest.fixture
def app(tmp_path: Path) -> Iterator[Flask]:
    application = create_app(
        Settings.for_testing(
            f"sqlite+pysqlite:///{tmp_path / 'today-v2.db'}",
            jwt_secret_key=JWT_SECRET,
        )
    )
    with application.app_context():
        engine = get_engine()
        Base.metadata.create_all(engine)
        with Session(engine) as session, session.begin():
            users = [
                User(
                    email_normalized=f"member-{index}@example.test",
                    password_hash="$argon2id$test-only",
                    status=UserStatus.ACTIVE,
                    role=UserRole.MEMBER,
                    token_version=0,
                    is_demo=False,
                )
                for index in (1, 2)
            ]
            session.add_all(users)
            session.flush()
            for index, user in enumerate(users, start=1):
                seed_user_starter(session, user, display_name=f"Member {index}")
            application.config["USER_IDS"] = [user.id for user in users]
        with Session(engine) as session:
            tokens = [
                create_access_token(session.get(User, user_id))[0]
                for user_id in application.config["USER_IDS"]
            ]
            application.config["TOKENS"] = tokens
    yield application
    with application.app_context():
        get_engine().dispose()


def _auth(app: Flask, index: int = 0) -> dict[str, str]:
    return {"Authorization": f"Bearer {app.config['TOKENS'][index]}"}


def _today(app: Flask, local_date: str = MONDAY, index: int = 0) -> dict[str, object]:
    response = app.test_client().get(f"/api/v1/today?date={local_date}", headers=_auth(app, index))
    assert response.status_code == 200
    return response.get_json()


def test_today_is_private_and_composes_effective_plan(app: Flask) -> None:
    client = app.test_client()
    assert client.get(f"/api/v1/today?date={MONDAY}").status_code == 401

    payload = _today(app)
    assert payload["local_date"] == MONDAY
    assert payload["user"]["email"] == "member-1@example.test"
    assert payload["planned_day"]["name"] == "Upper A — Incline + Back"
    assert payload["effective_day"]["id"] == payload["planned_day"]["id"]
    assert payload["exercise_plan"][1]["planned_sets"] == 3
    targets = {target["slug"]: target for target in payload["muscle_targets"]}
    assert targets["upper_chest"]["role"] == "primary"
    assert payload["water"]["total_ml"] == 0


def test_one_time_continue_and_swap_transitions(app: Flask) -> None:
    client = app.test_client()
    monday = _today(app)
    tuesday = _today(app, TUESDAY)

    one_time = client.put(
        "/api/v1/today/override",
        headers={**_auth(app), "Idempotency-Key": "override-once-001"},
        json={
            "local_date": MONDAY,
            "action": "replace",
            "effective_split_day_id": tuesday["planned_day"]["id"],
            "schedule_effect": "one_time",
            "expected_version": 0,
        },
    )
    assert one_time.status_code == 200
    assert one_time.get_json()["effective_day"]["id"] == tuesday["planned_day"]["id"]
    assert one_time.get_json()["schedule_version"] == 1

    assert (
        client.delete(
            f"/api/v1/today/override?local_date={MONDAY}&expected_version=1",
            headers=_auth(app),
        ).status_code
        == 204
    )
    swap = client.put(
        "/api/v1/today/override",
        headers={**_auth(app), "Idempotency-Key": "override-swap-001"},
        json={
            "local_date": MONDAY,
            "action": "swap",
            "effective_split_day_id": tuesday["planned_day"]["id"],
            "swap_target_local_date": TUESDAY,
            "schedule_effect": "swap_forward",
            "expected_version": 2,
        },
    )
    assert swap.status_code == 200
    swapped_target = _today(app, TUESDAY)
    assert swapped_target["effective_day"]["id"] == monday["planned_day"]["id"]
    with app.app_context(), Session(get_engine()) as session:
        rows = list(session.scalars(select(DailyPlanOverride)))
        assert len(rows) == 2
        assert len({row.swap_group_id for row in rows}) == 1


def test_continue_from_here_moves_cursor_after_selected_day(app: Flask) -> None:
    selected = _today(app, TUESDAY)["planned_day"]
    response = app.test_client().put(
        "/api/v1/today/override",
        headers={**_auth(app), "Idempotency-Key": "continue-here-001"},
        json={
            "local_date": MONDAY,
            "action": "replace",
            "effective_split_day_id": selected["id"],
            "schedule_effect": "continue_from_here",
            "expected_version": 0,
        },
    )
    assert response.status_code == 200
    with app.app_context(), Session(get_engine()) as session:
        state = session.get(ScheduleState, app.config["USER_IDS"][0])
        selected_row = session.get(SplitDay, selected["id"])
        next_row = session.scalar(
            select(SplitDay).where(
                SplitDay.split_id == selected_row.split_id,
                SplitDay.sequence == selected_row.sequence + 1,
            )
        )
        assert state.active_split_id == selected_row.split_id
        assert state.cursor_split_day_id == next_row.id
        assert state.version == 1


def test_skip_replay_and_version_conflict_advance_only_once(app: Flask) -> None:
    client = app.test_client()
    body = {"local_date": MONDAY, "schedule_effect": "advance", "expected_version": 0}
    headers = {**_auth(app), "Idempotency-Key": "skip-monday-0001"}
    first = client.post("/api/v1/today/skip", headers=headers, json=body)
    replay = client.post("/api/v1/today/skip", headers=headers, json=body)
    stale = client.post(
        "/api/v1/today/skip",
        headers={**_auth(app), "Idempotency-Key": "skip-monday-0002"},
        json=body,
    )

    assert first.status_code == replay.status_code == 200
    assert first.get_json()["schedule_version"] == replay.get_json()["schedule_version"] == 1
    assert stale.status_code == 409
    with app.app_context(), Session(get_engine()) as session:
        user_id = app.config["USER_IDS"][0]
        assert (
            session.scalar(
                select(func.count())
                .select_from(DailyPlanOverride)
                .where(DailyPlanOverride.user_id == user_id)
            )
            == 1
        )
        assert session.get(ScheduleState, user_id).version == 1


def test_today_only_exercise_edit_does_not_mutate_template(app: Flask) -> None:
    before = _today(app)
    original_ids = [item["exercise"]["id"] for item in before["exercise_plan"]]
    inputs = []
    for item in before["exercise_plan"][:2]:
        inputs.append(
            {
                "source_template_item_id": item["source_template_item_id"],
                "exercise_id": item["exercise"]["id"],
                "sequence": len(inputs),
                "item_type": item["item_type"],
                "planned_sets": item["planned_sets"],
                "rep_min": item["rep_min"],
                "rep_max": item["rep_max"],
                "rest_seconds": item["rest_seconds"],
                "target_rir": item["target_rir"],
                "optional": item["optional"],
                "notes": item["notes"],
            }
        )
    inputs[1]["exercise_id"] = "incline_dumbbell_press"
    response = app.test_client().put(
        "/api/v1/today/exercises",
        headers={**_auth(app), "Idempotency-Key": "edit-today-00001"},
        json={
            "local_date": MONDAY,
            "items": inputs,
            "scope": "today_only",
            "expected_version": 0,
        },
    )
    assert response.status_code == 200
    assert response.get_json()["exercise_plan"][1]["exercise"]["id"] == "incline_dumbbell_press"
    with app.app_context(), Session(get_engine()) as session:
        user_id = app.config["USER_IDS"][0]
        split_id = session.scalar(select(Split.id).where(Split.user_id == user_id, Split.is_active))
        day_id = session.scalar(
            select(SplitDay.id).where(SplitDay.split_id == split_id, SplitDay.sequence == 1)
        )
        stored = list(
            session.scalars(
                select(WorkoutTemplateItem)
                .where(WorkoutTemplateItem.split_day_id == day_id)
                .order_by(WorkoutTemplateItem.sequence)
            )
        )
        assert [item.exercise_id for item in stored] == original_ids


def test_explicit_save_to_split_updates_future_template(app: Flask) -> None:
    before = _today(app)
    source_day_id = before["effective_day"]["id"]
    first = before["exercise_plan"][0]
    response = app.test_client().put(
        "/api/v1/today/exercises",
        headers={**_auth(app), "Idempotency-Key": "save-split-00001"},
        json={
            "local_date": MONDAY,
            "source_split_day_id": source_day_id,
            "scope": "save_to_split",
            "expected_version": 0,
            "items": [
                {
                    "source_template_item_id": first["source_template_item_id"],
                    "exercise_id": "plank",
                    "sequence": 0,
                    "item_type": "core",
                    "planned_sets": 4,
                    "duration_seconds": 45,
                    "rest_seconds": 30,
                    "optional": False,
                }
            ],
        },
    )
    assert response.status_code == 200
    with app.app_context(), Session(get_engine()) as session:
        stored = list(
            session.scalars(
                select(WorkoutTemplateItem).where(WorkoutTemplateItem.split_day_id == source_day_id)
            )
        )
        assert len(stored) == 1
        assert stored[0].exercise_id == "plank"
        assert stored[0].sets == 4


def test_cross_tenant_split_day_is_not_attachable(app: Flask) -> None:
    foreign_day_id = _today(app, index=1)["planned_day"]["id"]
    denied = app.test_client().put(
        "/api/v1/today/override",
        headers={**_auth(app), "Idempotency-Key": "foreign-day-0001"},
        json={
            "local_date": MONDAY,
            "action": "replace",
            "effective_split_day_id": foreign_day_id,
            "schedule_effect": "one_time",
            "expected_version": 0,
        },
    )
    assert denied.status_code == 404
    assert _today(app)["schedule_version"] == 0
