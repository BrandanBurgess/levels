from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from importlib.resources import files
from typing import Any, cast
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import Engine, delete, func, select
from sqlalchemy.orm import Session

from levels_api.database import create_database_engine
from levels_api.models import (
    AppSettings,
    AvatarSettings,
    Exercise,
    ExerciseMuscle,
    MeasurementType,
    MuscleGroup,
    MuscleRole,
    PreferredUnits,
    Profile,
    ScheduleState,
    SessionExercise,
    SessionStatus,
    Split,
    SplitDay,
    TemplateAlternative,
    TemplateItemType,
    User,
    UserRole,
    UserStatus,
    VisibilitySettings,
    WorkoutSession,
    WorkoutTemplateItem,
)

DEFAULT_DATABASE_URL = "sqlite+pysqlite:///./levels-dev.db"
DEFAULT_SEED_EMAIL = "seed-owner@levels.local"
DEMO_EMAIL = "demo@levels.invalid"

SVG_REGIONS: dict[str, list[str]] = {
    "upper_chest": ["chest_upper"],
    "mid_chest": ["chest_mid"],
    "lower_chest": ["chest_lower"],
    "front_delts": ["delts_front"],
    "side_delts": ["delts_side"],
    "rear_delts": ["delts_rear"],
    "lats": ["lats"],
    "upper_back": ["upper_back"],
    "traps": ["traps"],
    "spinal_erectors": ["spinal_erectors"],
    "biceps": ["biceps"],
    "brachialis": ["brachialis"],
    "forearms": ["forearms"],
    "triceps": ["triceps"],
    "abs": ["abs"],
    "obliques": ["obliques"],
    "hip_flexors": ["hip_flexors"],
    "glutes": ["glutes"],
    "abductors": ["abductors"],
    "quads": ["quads"],
    "hamstrings": ["hamstrings"],
    "adductors": ["adductors"],
    "calves": ["calves"],
    "cardiovascular": [],
    "full_body": [],
}


@dataclass(frozen=True)
class SeedResult:
    muscle_groups: int
    exercises: int
    splits: int
    profile_id: str
    active_split_slug: str
    user_id: str


def _stable_id(kind: str, key: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"https://levels.app/seed/{kind}/{key}"))


def _load_json(name: str) -> dict[str, Any]:
    resource = files("levels_api.seed.data").joinpath(name)
    return cast(dict[str, Any], json.loads(resource.read_text(encoding="utf-8")))


def _seed_muscle_groups(session: Session, catalog: dict[str, Any]) -> None:
    for raw in cast(list[dict[str, Any]], catalog["muscle_groups"]):
        slug = str(raw["slug"])
        muscle = session.scalar(select(MuscleGroup).where(MuscleGroup.slug == slug))
        if muscle is None:
            muscle = MuscleGroup(id=str(raw["id"]), slug=slug)
            session.add(muscle)
        muscle.display_name = str(raw["display_name"])
        muscle.body_region = str(raw["body_region"])
        muscle.svg_region_ids = SVG_REGIONS[slug]
        muscle.highlightable = bool(muscle.svg_region_ids)


def _seed_exercises(session: Session, catalog: dict[str, Any]) -> None:
    session.flush()
    raw_exercises = cast(list[dict[str, Any]], catalog["exercises"])
    seeded_exercise_ids = [str(raw["id"]) for raw in raw_exercises]
    session.execute(
        delete(ExerciseMuscle).where(ExerciseMuscle.exercise_id.in_(seeded_exercise_ids))
    )

    for raw in cast(list[dict[str, Any]], catalog["exercises"]):
        slug = str(raw["slug"])
        exercise = session.scalar(
            select(Exercise).where(Exercise.slug == slug, Exercise.owner_user_id.is_(None))
        )
        if exercise is None:
            exercise = Exercise(id=str(raw["id"]), slug=slug)
            session.add(exercise)

        exercise.name = str(raw["name"])
        exercise.owner_user_id = None
        exercise.aliases = [str(alias) for alias in cast(list[str], raw["aliases"])]
        exercise.variation_group = str(raw["variation_group"])
        exercise.movement_pattern = str(raw["movement_pattern"])
        exercise.equipment = str(raw["equipment"])
        exercise.measurement_type = MeasurementType(str(raw["measurement_type"]))
        exercise.compound = bool(raw["compound"])
        exercise.unilateral = bool(raw["unilateral"])
        exercise.default_rep_min = cast(int | None, raw["default_rep_min"])
        exercise.default_rep_max = cast(int | None, raw["default_rep_max"])
        exercise.default_rest_seconds = cast(int | None, raw["default_rest_seconds"])
        exercise.progression_increment_kg = None
        exercise.automatic_progression_enabled = bool(raw["automatic_progression_enabled"])
        exercise.metadata_json = {
            "seed_schema_version": catalog["schema_version"],
            "style_tags": cast(list[str], raw["style_tags"]),
        }
        exercise.archived_at = datetime(1970, 1, 1, tzinfo=UTC) if bool(raw["archived"]) else None

    session.flush()
    for raw in cast(list[dict[str, Any]], catalog["exercises"]):
        for role, contribution, field in (
            (MuscleRole.PRIMARY, Decimal("1.000"), "primary_muscles"),
            (MuscleRole.SECONDARY, Decimal("0.450"), "secondary_muscles"),
        ):
            for muscle_id in cast(list[str], raw[field]):
                session.add(
                    ExerciseMuscle(
                        exercise_id=str(raw["id"]),
                        muscle_group_id=muscle_id,
                        role=role,
                        contribution=contribution,
                    )
                )


def _seed_profile(
    session: Session,
    data: dict[str, Any],
    user: User,
    display_name: str | None = None,
    timezone: str | None = None,
    preferred_units: PreferredUnits | None = None,
) -> tuple[Profile, AppSettings]:
    raw_profile = cast(dict[str, Any], data["profile"])
    profile = session.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is None:
        profile = Profile(id=_stable_id("profile", user.id), user_id=user.id)
        session.add(profile)

    profile.display_name = display_name or str(raw_profile["display_name"])
    profile.height_cm = int(raw_profile["height_cm"])
    profile.body_weight_kg = Decimal(str(raw_profile["body_weight_kg"]))
    profile.preferred_units = preferred_units or PreferredUnits(str(raw_profile["preferred_units"]))
    profile.timezone = timezone or str(raw_profile["timezone"])
    profile.avatar_variant = "brandan-original-v1"
    session.flush()

    visibility = session.scalar(
        select(VisibilitySettings).where(VisibilitySettings.profile_id == profile.id)
    )
    if visibility is None:
        visibility = VisibilitySettings(
            id=_stable_id("visibility", user.id),
            profile_id=profile.id,
            show_height=True,
            show_body_weight=False,
            show_water=False,
            show_session_summaries=True,
            show_set_details=False,
            show_public_notes=False,
            show_progress_charts=True,
            show_personal_records=True,
            show_readiness=False,
        )
        session.add(visibility)

    raw_settings = cast(dict[str, Any], data["settings"])
    settings = session.scalar(select(AppSettings).where(AppSettings.profile_id == profile.id))
    if settings is None:
        settings = AppSettings(id=_stable_id("settings", user.id), profile_id=profile.id)
        session.add(settings)
    settings.week_starts_on = 1
    settings.default_water_goal_ml = int(raw_settings["default_water_goal_ml"])
    settings.water_quick_add_ml = [
        int(amount) for amount in cast(list[int], raw_settings["water_quick_add_ml"])
    ]
    settings.primary_muscle_weight = Decimal("1.0")
    settings.secondary_muscle_weight = Decimal("0.45")
    settings.default_target_rir = Decimal(str(raw_settings["default_target_rir"]))
    settings.default_load_increment_kg = Decimal(str(raw_settings["default_load_increment_kg"]))
    return profile, settings


def _items_for_day(raw_day: dict[str, Any]) -> list[dict[str, Any]]:
    items = raw_day.get("items")
    if items is not None:
        return cast(list[dict[str, Any]], items)
    modes = cast(dict[str, list[dict[str, Any]]], raw_day["modes"])
    return modes["conditioning"]


def _recommended_weekday(is_active: bool, sequence: int) -> int | None:
    if not is_active:
        return None
    return {1: 0, 2: 1, 3: 3, 4: 4, 5: 5}.get(sequence)


def _seed_template_items(
    session: Session, user_id: str, split: Split, day: SplitDay, raw_day: dict[str, Any]
) -> None:
    for sequence, raw in enumerate(_items_for_day(raw_day), start=1):
        item_id = _stable_id("template-item", f"{user_id}:{split.slug}:{day.sequence}:{sequence}")
        item = session.get(WorkoutTemplateItem, item_id)
        if item is None:
            item = WorkoutTemplateItem(id=item_id, split_day_id=day.id, sequence=sequence)
            session.add(item)
        item.exercise_id = str(raw["exercise_id"])
        item.item_type = TemplateItemType(str(raw["item_type"]))
        item.sets = int(raw["sets"])
        item.rep_min = cast(int | None, raw["rep_min"])
        item.rep_max = cast(int | None, raw["rep_max"])
        item.duration_seconds = None
        item.distance_meters = None
        item.rest_seconds = cast(int | None, raw["rest_seconds"])
        target_rir = raw["target_rir"]
        item.target_rir = Decimal(str(target_rir)) if target_rir is not None else None
        item.superset_group = cast(str | None, raw["superset_group"])
        item.notes = cast(str | None, raw["notes"])
        item.optional = bool(raw["optional"])
        session.flush()

        session.execute(
            delete(TemplateAlternative).where(TemplateAlternative.template_item_id == item.id)
        )
        for alternative_sequence, exercise_id in enumerate(
            cast(list[str], raw["alternatives"]), start=1
        ):
            session.add(
                TemplateAlternative(
                    template_item_id=item.id,
                    exercise_id=exercise_id,
                    sequence=alternative_sequence,
                )
            )


def _seed_splits(session: Session, data: dict[str, Any], user_id: str) -> Split:
    active_split: Split | None = None
    for display_order, raw_split in enumerate(cast(list[dict[str, Any]], data["splits"]), start=1):
        slug = str(raw_split["slug"])
        split = session.scalar(select(Split).where(Split.user_id == user_id, Split.slug == slug))
        if split is None:
            split = Split(id=_stable_id("split", f"{user_id}:{slug}"), user_id=user_id, slug=slug)
            session.add(split)
        split.name = str(raw_split["name"])
        split.description = str(raw_split["description"])
        split.is_active = bool(raw_split["is_active"])
        split.is_seeded = True
        split.display_order = display_order
        split.archived_at = None
        session.flush()

        for raw_day in cast(list[dict[str, Any]], raw_split["days"]):
            sequence = int(raw_day["sequence"])
            day_id = _stable_id("split-day", f"{user_id}:{slug}:{sequence}")
            day = session.get(SplitDay, day_id)
            if day is None:
                day = SplitDay(id=day_id, split_id=split.id, sequence=sequence)
                session.add(day)
            day.name = str(raw_day["name"])
            day.day_type = str(raw_day["day_type"])
            day.recommended_weekday = _recommended_weekday(split.is_active, sequence)
            day.description = None
            day.is_optional = bool(raw_day.get("is_optional", False))
            session.flush()
            _seed_template_items(session, user_id, split, day, raw_day)

        if split.is_active:
            active_split = split

    if active_split is None:
        raise ValueError("Seed data must contain exactly one active split")
    return active_split


def _ensure_seed_user(session: Session) -> User:
    user = session.scalar(select(User).where(User.email_normalized == DEFAULT_SEED_EMAIL))
    if user is None:
        user = User(
            id=_stable_id("user", DEFAULT_SEED_EMAIL),
            email_normalized=DEFAULT_SEED_EMAIL,
            password_hash="$argon2id$seed-user-has-no-login",
            status=UserStatus.ACTIVE,
            role=UserRole.MEMBER,
            token_version=0,
            is_demo=False,
        )
        session.add(user)
        session.flush()
    return user


def seed_user_starter(
    session: Session,
    user: User,
    *,
    display_name: str | None = None,
    timezone: str | None = None,
    preferred_units: PreferredUnits | None = None,
) -> SeedResult:
    """Create an idempotent tenant-owned starter profile, settings, splits, and schedule."""
    catalog = _load_json("exercise_catalog.json")
    split_data = _load_json("seed_splits.json")
    _seed_muscle_groups(session, catalog)
    _seed_exercises(session, catalog)
    profile, settings = _seed_profile(
        session, split_data, user, display_name, timezone, preferred_units
    )
    active_split = _seed_splits(session, split_data, user.id)
    settings.active_split_id = active_split.id
    first_day = session.scalar(
        select(SplitDay).where(SplitDay.split_id == active_split.id).order_by(SplitDay.sequence)
    )
    avatar = session.get(AvatarSettings, user.id)
    if avatar is None:
        session.add(AvatarSettings(user_id=user.id))
    schedule = session.get(ScheduleState, user.id)
    if schedule is None:
        session.add(
            ScheduleState(
                user_id=user.id,
                active_split_id=active_split.id,
                cursor_split_day_id=first_day.id if first_day else None,
                cursor_effective_date=datetime.now(UTC).date(),
                version=0,
            )
        )
    else:
        schedule.active_split_id = active_split.id
        if schedule.cursor_split_day_id is None and first_day is not None:
            schedule.cursor_split_day_id = first_day.id
    session.flush()

    return SeedResult(
        muscle_groups=session.scalar(select(func.count()).select_from(MuscleGroup)) or 0,
        exercises=session.scalar(select(func.count()).select_from(Exercise)) or 0,
        splits=session.scalar(select(func.count()).select_from(Split)) or 0,
        profile_id=profile.id,
        active_split_slug=active_split.slug,
        user_id=user.id,
    )


def seed_session(session: Session, user: User | None = None) -> SeedResult:
    return seed_user_starter(session, user or _ensure_seed_user(session))


def seed_demo_session(session: Session) -> SeedResult:
    """Seed a fixed fictional tenant used exclusively by anonymous GET demo APIs."""
    demo = session.scalar(select(User).where(User.email_normalized == DEMO_EMAIL))
    if demo is None:
        demo = User(
            id=_stable_id("user", DEMO_EMAIL),
            email_normalized=DEMO_EMAIL,
            password_hash="$argon2id$demo-has-no-credentials",
            status=UserStatus.DISABLED,
            role=UserRole.MEMBER,
            token_version=0,
            is_demo=True,
        )
        session.add(demo)
        session.flush()
    result = seed_user_starter(
        session,
        demo,
        display_name="Alex Rivers",
        timezone="America/Toronto",
        preferred_units=PreferredUnits.METRIC,
    )
    splits = session.scalars(
        select(Split).where(Split.user_id == demo.id).order_by(Split.display_order)
    ).all()
    if splits:
        splits[0].name = "Alex's Athletic Upper/Lower"
    if len(splits) > 1:
        splits[1].name = "Alex's Bodyweight Conditioning"

    existing_session = session.scalar(
        select(WorkoutSession.id).where(WorkoutSession.user_id == demo.id).limit(1)
    )
    if existing_session is None:
        active_split = next((split for split in splits if split.is_active), None)
        demo_days = list(active_split.days[:2]) if active_split is not None else []
        for index, day in enumerate(demo_days):
            completed_at = datetime(2026, 7, 12 + index, 18, 0, tzinfo=UTC)
            workout = WorkoutSession(
                id=_stable_id("demo-session", str(index)),
                user_id=demo.id,
                version=0,
                split_day_id=day.id,
                session_date_local=completed_at.date(),
                started_at=completed_at,
                completed_at=completed_at,
                status=SessionStatus.COMPLETED,
                title=day.name,
            )
            session.add(workout)
            for sequence, item in enumerate(day.items[:4]):
                exercise = session.get(Exercise, item.exercise_id)
                if exercise is None:
                    continue
                session.add(
                    SessionExercise(
                        id=_stable_id("demo-session-exercise", f"{index}:{sequence}"),
                        workout_session_id=workout.id,
                        exercise_id=exercise.id,
                        source_template_item_id=item.id,
                        sequence=sequence,
                        planned_sets=item.sets,
                        item_type=item.item_type,
                        display_name_snapshot=exercise.name,
                        variation_group_snapshot=exercise.variation_group,
                        rep_min_snapshot=item.rep_min,
                        rep_max_snapshot=item.rep_max,
                        duration_seconds_snapshot=item.duration_seconds,
                        distance_meters_snapshot=item.distance_meters,
                        rounds_target_snapshot=item.rounds_target,
                        rest_seconds_snapshot=item.rest_seconds,
                        target_rir_snapshot=item.target_rir,
                        optional_snapshot=item.optional,
                    )
                )
    session.flush()
    return result


def seed_database(database_url: str | None = None) -> SeedResult:
    resolved_url = database_url or os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL
    engine: Engine = create_database_engine(resolved_url, os.getenv("TURSO_AUTH_TOKEN"))
    try:
        with Session(engine) as session, session.begin():
            result = seed_session(session)
            seed_demo_session(session)
            return result
    finally:
        engine.dispose()


def main() -> None:
    result = seed_database()
    print(
        "Seed complete: "
        f"{result.muscle_groups} muscle groups, {result.exercises} exercises, "
        f"{result.splits} splits; active split={result.active_split_slug}"
    )
