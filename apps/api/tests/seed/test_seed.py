from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from levels_api.models import (
    AppSettings,
    Base,
    Exercise,
    ExerciseMuscle,
    MuscleGroup,
    MuscleRole,
    Profile,
    Split,
    SplitDay,
    VisibilitySettings,
    WorkoutTemplateItem,
)
from levels_api.seed import seed_session

REPO_ROOT = Path(__file__).parents[4]
HANDOFF_ROOT = REPO_ROOT / "docs" / "levels_product_handoff" / "levels_product_handoff"
PACKAGED_DATA = REPO_ROOT / "apps" / "api" / "src" / "levels_api" / "seed" / "data"


@pytest.fixture
def seeded_session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'seed.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_session(session)
        session.commit()
        yield session
    engine.dispose()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_packaged_seed_assets_match_handoff_exactly() -> None:
    assert _sha256(PACKAGED_DATA / "exercise_catalog.json") == _sha256(
        HANDOFF_ROOT / "13_EXERCISE_CATALOG.json"
    )
    assert _sha256(PACKAGED_DATA / "seed_splits.json") == _sha256(
        HANDOFF_ROOT / "14_SEED_SPLITS.json"
    )


def test_seed_is_idempotent_and_selects_active_split(seeded_session: Session) -> None:
    first = seed_session(seeded_session)
    seeded_session.commit()
    second = seed_session(seeded_session)
    seeded_session.commit()

    assert first == second
    assert second.muscle_groups == 25
    assert second.exercises == 98
    assert second.splits == 2
    assert second.active_split_slug == "brandan-athletic-upper-lower"
    assert seeded_session.scalar(select(func.count()).select_from(Profile)) == 1
    assert seeded_session.scalar(select(func.count()).select_from(VisibilitySettings)) == 1
    assert seeded_session.scalar(select(func.count()).select_from(AppSettings)) == 1
    assert seeded_session.scalar(select(func.count()).select_from(ExerciseMuscle)) == 277


def test_seeded_profile_is_private_by_default(seeded_session: Session) -> None:
    profile = seeded_session.scalar(select(Profile))
    assert profile is not None
    assert profile.display_name == "Brandan Burgess"
    assert profile.visibility is not None
    assert profile.visibility.show_height is True
    assert profile.visibility.show_body_weight is False
    assert profile.visibility.show_water is False
    assert profile.visibility.show_set_details is False
    assert profile.settings is not None
    assert profile.settings.active_split is not None
    assert profile.settings.active_split.slug == "brandan-athletic-upper-lower"


def test_active_schedule_and_optional_day_are_normalized(seeded_session: Session) -> None:
    split = seeded_session.scalar(select(Split).where(Split.slug == "brandan-athletic-upper-lower"))
    assert split is not None
    assert [day.recommended_weekday for day in split.days] == [0, 1, 3, 4, 5]
    optional_day = split.days[-1]
    assert optional_day.is_optional is True
    assert optional_day.day_type == "optional"
    assert [item.exercise_id for item in optional_day.items] == [
        "stationary_bike_easy",
        "stationary_bike_intervals",
        "farmer_carry",
        "plank",
        "side_plank",
    ]


def test_every_highlightable_muscle_maps_to_stable_svg_regions(
    seeded_session: Session,
) -> None:
    muscles = seeded_session.scalars(select(MuscleGroup)).all()
    assert muscles
    assert all(muscle.svg_region_ids for muscle in muscles if muscle.highlightable)
    assert {muscle.slug for muscle in muscles if not muscle.highlightable} == {
        "cardiovascular",
        "full_body",
    }


def test_upper_a_starts_with_requested_incline_and_back_focus(
    seeded_session: Session,
) -> None:
    day = seeded_session.scalar(select(SplitDay).where(SplitDay.name == "Upper A — Incline + Back"))
    assert day is not None
    exercises = [item.exercise_id for item in day.items]
    assert exercises[1:4] == [
        "incline_barbell_bench_press",
        "pull_up",
        "chest_supported_row",
    ]
    incline = seeded_session.scalar(
        select(Exercise).where(Exercise.id == "incline_barbell_bench_press")
    )
    assert incline is not None
    assert {(link.muscle_group_id, link.role) for link in incline.muscle_links} >= {
        ("upper_chest", MuscleRole.PRIMARY),
        ("mid_chest", MuscleRole.SECONDARY),
        ("front_delts", MuscleRole.SECONDARY),
    }


def test_catalog_contains_no_deadlift_variations(seeded_session: Session) -> None:
    exercises = seeded_session.scalars(select(Exercise)).all()
    searchable_text = " ".join(
        value
        for exercise in exercises
        for value in [exercise.slug, exercise.name, *exercise.aliases]
    )
    assert "deadlift" not in searchable_text.casefold()


def test_seeded_template_rows_reference_existing_exercises(seeded_session: Session) -> None:
    exercise_ids = set(seeded_session.scalars(select(Exercise.id)))
    template_exercise_ids = set(seeded_session.scalars(select(WorkoutTemplateItem.exercise_id)))
    assert template_exercise_ids <= exercise_ids
