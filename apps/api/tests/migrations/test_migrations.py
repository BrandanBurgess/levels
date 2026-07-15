from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import MetaData, create_engine, inspect, select
from sqlalchemy.orm import Session

from levels_api.models import Base
from levels_api.seed import seed_demo_session

API_ROOT = Path(__file__).resolve().parents[2]


def alembic_config(database_url: str) -> Config:
    config = Config(API_ROOT / "alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _insert_populated_v1_fixture(database_url: str) -> None:
    engine = create_engine(database_url)
    metadata = MetaData()
    metadata.reflect(engine)
    now = datetime(2025, 6, 1, 14, 30, tzinfo=UTC)
    ids = {
        "profile": "00000000-0000-0000-0000-000000000001",
        "split": "00000000-0000-0000-0000-000000000002",
        "day": "00000000-0000-0000-0000-000000000003",
        "exercise": "00000000-0000-0000-0000-000000000004",
        "item": "00000000-0000-0000-0000-000000000005",
        "session": "00000000-0000-0000-0000-000000000006",
        "session_exercise": "00000000-0000-0000-0000-000000000007",
        "set": "00000000-0000-0000-0000-000000000008",
    }
    with engine.begin() as connection:
        connection.execute(
            metadata.tables["exercises"].insert(),
            {
                "id": ids["exercise"],
                "slug": "migration-bench-press",
                "name": "Migration Bench Press",
                "aliases": [],
                "variation_group": "bench-press",
                "movement_pattern": "horizontal_push",
                "equipment": "barbell",
                "measurement_type": "load_reps",
                "compound": True,
                "unilateral": False,
                "default_rep_min": 5,
                "default_rep_max": 8,
                "default_rest_seconds": 180,
                "progression_increment_kg": 2.5,
                "automatic_progression_enabled": True,
                "metadata_json": {},
                "archived_at": None,
                "created_at": now,
                "updated_at": now,
            },
        )
        connection.execute(
            metadata.tables["profiles"].insert(),
            {
                "id": ids["profile"],
                "display_name": "Existing Member",
                "height_cm": 180,
                "body_weight_kg": 82.5,
                "preferred_units": "metric",
                "timezone": "America/Toronto",
                "avatar_variant": "brandan-original-v1",
                "created_at": now,
                "updated_at": now,
            },
        )
        connection.execute(
            metadata.tables["splits"].insert(),
            {
                "id": ids["split"],
                "name": "Existing Split",
                "slug": "existing-split",
                "description": "Must survive v2 migration",
                "is_active": True,
                "is_seeded": True,
                "display_order": 0,
                "archived_at": None,
                "created_at": now,
                "updated_at": now,
            },
        )
        connection.execute(
            metadata.tables["split_days"].insert(),
            {
                "id": ids["day"],
                "split_id": ids["split"],
                "name": "Push",
                "day_type": "push",
                "sequence": 0,
                "recommended_weekday": 0,
                "description": None,
                "is_optional": False,
            },
        )
        connection.execute(
            metadata.tables["workout_template_items"].insert(),
            {
                "id": ids["item"],
                "split_day_id": ids["day"],
                "exercise_id": ids["exercise"],
                "sequence": 0,
                "item_type": "main",
                "sets": 4,
                "rep_min": 5,
                "rep_max": 8,
                "duration_seconds": None,
                "distance_meters": None,
                "rest_seconds": 180,
                "target_rir": 2,
                "superset_group": None,
                "notes": "Preserve prescription",
                "optional": False,
            },
        )
        connection.execute(
            metadata.tables["app_settings"].insert(),
            {
                "id": "00000000-0000-0000-0000-000000000009",
                "profile_id": ids["profile"],
                "active_split_id": ids["split"],
                "week_starts_on": 1,
                "default_water_goal_ml": 2800,
                "water_quick_add_ml": [250, 500],
                "primary_muscle_weight": 1,
                "secondary_muscle_weight": 0.45,
                "default_target_rir": 2,
                "default_load_increment_kg": 1.133981,
                "reduced_motion_override": None,
                "created_at": now,
                "updated_at": now,
            },
        )
        connection.execute(
            metadata.tables["workout_sessions"].insert(),
            {
                "id": ids["session"],
                "split_day_id": ids["day"],
                "session_date_local": date(2025, 6, 1),
                "started_at": now,
                "completed_at": now,
                "status": "completed",
                "title": "Historic Push",
                "public_visibility": "private",
                "perceived_effort": 8,
                "notes_private": "Keep me",
                "notes_public": None,
                "deleted_at": None,
                "idempotency_key": "historic-session",
                "created_at": now,
                "updated_at": now,
            },
        )
        connection.execute(
            metadata.tables["session_exercises"].insert(),
            {
                "id": ids["session_exercise"],
                "workout_session_id": ids["session"],
                "exercise_id": ids["exercise"],
                "source_template_item_id": ids["item"],
                "sequence": 0,
                "display_name_snapshot": "Historic Bench Press",
                "variation_group_snapshot": "bench-press",
                "rep_min_snapshot": 5,
                "rep_max_snapshot": 8,
                "target_rir_snapshot": 2,
                "notes": None,
                "substitution_reason": None,
            },
        )
        connection.execute(
            metadata.tables["set_logs"].insert(),
            {
                "id": ids["set"],
                "session_exercise_id": ids["session_exercise"],
                "sequence": 0,
                "set_type": "working",
                "load_kg": 100,
                "reps": 6,
                "rir": 2,
                "duration_seconds": None,
                "distance_meters": None,
                "rounds": None,
                "bodyweight_assistance_kg": None,
                "form_quality": 4,
                "pain_flag": False,
                "completed_at": now,
                "notes": "historic set",
                "deleted_at": None,
                "idempotency_key": "historic-set",
            },
        )
        tenant_roots = {
            "readiness_logs": {
                "id": "00000000-0000-0000-0000-000000000010",
                "local_date": date(2025, 6, 1),
                "energy": 4,
                "soreness": 2,
                "sleep_quality": 4,
                "pain_flag": False,
                "note_private": "ready",
                "created_at": now,
                "updated_at": now,
            },
            "water_logs": {
                "id": "00000000-0000-0000-0000-000000000011",
                "occurred_at": now,
                "local_date": date(2025, 6, 1),
                "amount_ml": 500,
                "source": "quick_add",
                "note": None,
                "created_at": now,
                "idempotency_key": "historic-water",
            },
            "personal_records": {
                "id": "00000000-0000-0000-0000-000000000012",
                "exercise_id": ids["exercise"],
                "record_type": "max_load",
                "value_numeric": 100,
                "unit": "kg",
                "reps_context": 6,
                "set_log_id": ids["set"],
                "achieved_at": now,
                "is_current": True,
                "created_at": now,
            },
            "achievements": {
                "id": "00000000-0000-0000-0000-000000000013",
                "achievement_type": "personal_record",
                "exercise_id": ids["exercise"],
                "set_log_id": ids["set"],
                "title": "Historic PR",
                "message": "Preserved",
                "achieved_at": now,
                "public": False,
                "idempotency_key": "historic-achievement",
            },
            "progression_suggestions": {
                "id": "00000000-0000-0000-0000-000000000014",
                "local_date": date(2025, 6, 1),
                "exercise_id": ids["exercise"],
                "suggestion_type": "load",
                "suggested_delta": 2.5,
                "confidence": "high",
                "explanation_json": ["historic evidence"],
                "source_session_ids_json": [ids["session"]],
                "accepted_at": None,
                "dismissed_at": None,
                "created_at": now,
            },
        }
        for table_name, values in tenant_roots.items():
            connection.execute(metadata.tables[table_name].insert(), values)
    engine.dispose()


def test_empty_database_upgrade_downgrade_and_reupgrade(tmp_path: Path) -> None:
    database_path = tmp_path / "migration-test.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    config = alembic_config(database_url)

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    expected_tables = set(Base.metadata.tables)
    assert set(inspect(engine).get_table_names()) == expected_tables | {"alembic_version"}

    with Session(engine) as session, session.begin():
        seed_demo_session(session)

    command.downgrade(config, "base")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}

    command.upgrade(config, "head")
    assert set(inspect(engine).get_table_names()) == expected_tables | {"alembic_version"}
    engine.dispose()


def test_populated_v1_requires_identity_and_preserves_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "populated-v1.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    config = alembic_config(database_url)
    command.upgrade(config, "a91f6028df36")
    _insert_populated_v1_fixture(database_url)

    monkeypatch.delenv("BOOTSTRAP_OWNER_EMAIL", raising=False)
    monkeypatch.delenv("BOOTSTRAP_OWNER_PASSWORD_HASH", raising=False)
    with pytest.raises(RuntimeError, match="BOOTSTRAP_OWNER_EMAIL"):
        command.upgrade(config, "head")

    monkeypatch.setenv("BOOTSTRAP_OWNER_EMAIL", "Owner@Example.COM")
    monkeypatch.setenv("BOOTSTRAP_OWNER_PASSWORD_HASH", "$argon2id$fixture")
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    metadata = MetaData()
    metadata.reflect(engine)
    with engine.connect() as connection:
        users = connection.execute(select(metadata.tables["users"])).mappings().all()
        assert len(users) == 2
        owner = next(user for user in users if not user["is_demo"])
        demo = next(user for user in users if user["is_demo"])
        user_id = owner["id"]
        assert owner["email_normalized"] == "owner@example.com"
        assert owner["password_hash"] == "$argon2id$fixture"
        assert demo["email_normalized"] == "demo@levels.invalid"
        assert demo["status"] == "disabled"

        for table_name in (
            "profiles",
            "splits",
            "workout_sessions",
            "readiness_logs",
            "water_logs",
            "personal_records",
            "achievements",
            "progression_suggestions",
        ):
            rows = (
                connection.execute(
                    select(metadata.tables[table_name]).where(
                        metadata.tables[table_name].c.user_id == user_id
                    )
                )
                .mappings()
                .all()
            )
            assert rows, table_name
            assert {row["user_id"] for row in rows} == {user_id}

        session = (
            connection.execute(
                select(metadata.tables["workout_sessions"]).where(
                    metadata.tables["workout_sessions"].c.id
                    == "00000000-0000-0000-0000-000000000006"
                )
            )
            .mappings()
            .one()
        )
        assert session["title"] == "Historic Push"
        assert session["completed_at"] is not None
        assert session["version"] == 0

        session_exercise = (
            connection.execute(select(metadata.tables["session_exercises"])).mappings().one()
        )
        assert session_exercise["display_name_snapshot"] == "Historic Bench Press"
        assert session_exercise["planned_sets"] == 4
        assert session_exercise["item_type"] == "main"
        assert session_exercise["rest_seconds_snapshot"] == 180
        assert session_exercise["optional_snapshot"] is False

        set_log = connection.execute(select(metadata.tables["set_logs"])).mappings().one()
        assert set_log["id"] == "00000000-0000-0000-0000-000000000008"
        assert set_log["load_kg"] == 100
        assert set_log["reps"] == 6

        avatar = (
            connection.execute(
                select(metadata.tables["avatar_settings"]).where(
                    metadata.tables["avatar_settings"].c.user_id == user_id
                )
            )
            .mappings()
            .one()
        )
        schedule = (
            connection.execute(
                select(metadata.tables["schedule_state"]).where(
                    metadata.tables["schedule_state"].c.user_id == user_id
                )
            )
            .mappings()
            .one()
        )
        assert avatar["user_id"] == user_id
        assert schedule["user_id"] == user_id
        assert schedule["active_split_id"] == "00000000-0000-0000-0000-000000000002"
        assert schedule["cursor_split_day_id"] == "00000000-0000-0000-0000-000000000003"

    engine.dispose()


def test_migration_head_matches_model_metadata(tmp_path: Path) -> None:
    database_path = tmp_path / "drift-test.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    config = alembic_config(database_url)
    command.upgrade(config, "head")
    engine = create_engine(database_url)

    with engine.connect() as connection:
        context = MigrationContext.configure(
            connection,
            opts={"compare_type": True, "render_as_batch": True},
        )
        assert compare_metadata(context, Base.metadata) == []

    engine.dispose()
