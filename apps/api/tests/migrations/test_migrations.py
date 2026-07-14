from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from levels_api.models import Base

API_ROOT = Path(__file__).resolve().parents[2]


def alembic_config(database_url: str) -> Config:
    config = Config(API_ROOT / "alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_empty_database_upgrade_downgrade_and_reupgrade(tmp_path: Path) -> None:
    database_path = tmp_path / "migration-test.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    config = alembic_config(database_url)

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    expected_tables = set(Base.metadata.tables)
    assert set(inspect(engine).get_table_names()) == expected_tables | {"alembic_version"}

    command.downgrade(config, "base")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}

    command.upgrade(config, "head")
    assert set(inspect(engine).get_table_names()) == expected_tables | {"alembic_version"}
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
