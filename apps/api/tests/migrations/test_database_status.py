from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, delete
from sqlalchemy.orm import Session

from levels_api.models import Exercise
from levels_api.scripts.database_status import verify_database
from levels_api.seed import seed_session

API_ROOT = Path(__file__).resolve().parents[2]


def _seeded_engine(tmp_path: Path) -> Engine:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'status.db').as_posix()}"
    config = Config(API_ROOT / "alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    with Session(engine) as session, session.begin():
        seed_session(session)
    return engine


def test_database_status_accepts_migrated_seeded_database(tmp_path: Path) -> None:
    engine = _seeded_engine(tmp_path)
    try:
        status = verify_database(engine)
    finally:
        engine.dispose()

    assert status.revision == "a91f6028df36"
    assert status.active_split_slug == "brandan-athletic-upper-lower"


def test_database_status_rejects_incomplete_seed(tmp_path: Path) -> None:
    engine = _seeded_engine(tmp_path)
    with Session(engine) as session, session.begin():
        session.execute(delete(Exercise).where(Exercise.slug == "high_bar_back_squat"))

    try:
        with pytest.raises(RuntimeError, match="Seed verification failed"):
            verify_database(engine)
    finally:
        engine.dispose()
