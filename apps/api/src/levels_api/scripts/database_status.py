from __future__ import annotations

import os
from dataclasses import dataclass

from alembic.runtime.migration import MigrationContext
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from levels_api.config import DEFAULT_DATABASE_URL
from levels_api.database import create_database_engine
from levels_api.models import Exercise, MuscleGroup, Profile, Split, User
from levels_api.seed.loader import DEFAULT_SEED_EMAIL, DEMO_EMAIL


@dataclass(frozen=True, slots=True)
class DatabaseStatus:
    revision: str
    muscle_groups: int
    exercises: int
    splits: int
    profiles: int
    active_split_slug: str


def verify_database(engine: Engine) -> DatabaseStatus:
    with engine.connect() as connection:
        revision = MigrationContext.configure(connection).get_current_revision()

    with Session(engine) as session:
        muscle_groups = session.scalar(select(func.count()).select_from(MuscleGroup)) or 0
        exercises = session.scalar(select(func.count()).select_from(Exercise)) or 0
        splits = session.scalar(select(func.count()).select_from(Split)) or 0
        profiles = session.scalar(select(func.count()).select_from(Profile)) or 0
        active_splits = session.scalars(select(Split).where(Split.is_active.is_(True))).all()
        bootstrap_user = session.scalar(
            select(User).where(User.email_normalized == DEFAULT_SEED_EMAIL)
        )
        demo_user = session.scalar(select(User).where(User.email_normalized == DEMO_EMAIL))
        catalog = session.scalars(select(Exercise)).all()

    if revision is None:
        raise RuntimeError("Database has no Alembic revision")
    if muscle_groups != 25 or exercises != 98 or splits < 2 or profiles < 1:
        raise RuntimeError(
            "Seed verification failed: expected 25 muscle groups, 98 exercises, "
            "and a populated fictional demo tenant"
        )
    if demo_user is None or not demo_user.is_demo:
        raise RuntimeError("Seed verification failed: missing fictional demo tenant")
    tenant_active_splits = {split.user_id: split for split in active_splits}
    if len(active_splits) != len(tenant_active_splits):
        raise RuntimeError("Seed verification failed: expected one active split per tenant")
    verified_user = bootstrap_user or demo_user
    verified_active_split = tenant_active_splits.get(verified_user.id)
    if (
        verified_active_split is None
        or verified_active_split.slug != "brandan-athletic-upper-lower"
    ):
        raise RuntimeError("Seed verification failed: unexpected active split")
    searchable_catalog = " ".join(
        value for exercise in catalog for value in (exercise.slug, exercise.name, *exercise.aliases)
    )
    if "deadlift" in searchable_catalog.casefold():
        raise RuntimeError("Seed verification failed: deadlift variation found")

    return DatabaseStatus(
        revision=revision,
        muscle_groups=muscle_groups,
        exercises=exercises,
        splits=splits,
        profiles=profiles,
        active_split_slug=verified_active_split.slug,
    )


def main() -> None:
    database_url = os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL
    engine = create_database_engine(database_url, os.getenv("TURSO_AUTH_TOKEN"))
    try:
        status = verify_database(engine)
    finally:
        engine.dispose()
    print(
        "Database verified: "
        f"revision={status.revision}, muscles={status.muscle_groups}, "
        f"exercises={status.exercises}, splits={status.splits}, "
        f"profiles={status.profiles}, active_split={status.active_split_slug}"
    )


if __name__ == "__main__":
    main()
