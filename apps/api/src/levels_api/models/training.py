from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IdMixin, TimestampMixin, utc_now
from .enums import (
    PublicVisibility,
    SessionStatus,
    SetType,
    TemplateItemType,
    WaterSource,
    enum_values,
)

if TYPE_CHECKING:
    from .catalog import Exercise
    from .progress import Achievement, PersonalRecord


class Split(IdMixin, TimestampMixin, Base):
    __tablename__ = "splits"
    __table_args__ = (
        UniqueConstraint("user_id", "slug", name="uq_splits_user_slug"),
        Index("idx_splits_user_archived_order", "user_id", "archived_at", "display_order"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_seeded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    archived_at: Mapped[datetime | None]

    days: Mapped[list[SplitDay]] = relationship(
        back_populates="split",
        cascade="all, delete-orphan",
        order_by="SplitDay.sequence",
    )


class SplitDay(IdMixin, Base):
    __tablename__ = "split_days"
    __table_args__ = (
        CheckConstraint(
            "recommended_weekday IS NULL OR recommended_weekday BETWEEN 0 AND 6",
            name="ck_split_days_recommended_weekday",
        ),
        UniqueConstraint("split_id", "sequence", name="uq_split_days_split_sequence"),
        Index("idx_split_days_split_sequence", "split_id", "sequence"),
    )

    split_id: Mapped[str] = mapped_column(ForeignKey("splits.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    day_type: Mapped[str] = mapped_column(String(50), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    recommended_weekday: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    split: Mapped[Split] = relationship(back_populates="days")
    items: Mapped[list[WorkoutTemplateItem]] = relationship(
        back_populates="split_day",
        cascade="all, delete-orphan",
        order_by="WorkoutTemplateItem.sequence",
    )
    sessions: Mapped[list[WorkoutSession]] = relationship(back_populates="split_day")


class WorkoutTemplateItem(IdMixin, Base):
    __tablename__ = "workout_template_items"
    __table_args__ = (
        CheckConstraint("sets BETWEEN 1 AND 20", name="ck_template_items_sets"),
        CheckConstraint(
            "target_rir IS NULL OR target_rir BETWEEN 0 AND 10",
            name="ck_template_items_target_rir",
        ),
        CheckConstraint("rep_min IS NULL OR rep_min >= 0", name="ck_template_items_rep_min"),
        CheckConstraint("rep_max IS NULL OR rep_max >= rep_min", name="ck_template_items_rep_max"),
        UniqueConstraint("split_day_id", "sequence", name="uq_template_items_day_sequence"),
        Index("idx_template_items_day_sequence", "split_day_id", "sequence"),
    )

    split_day_id: Mapped[str] = mapped_column(ForeignKey("split_days.id", ondelete="CASCADE"))
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"))
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    item_type: Mapped[TemplateItemType] = mapped_column(
        Enum(
            TemplateItemType,
            native_enum=False,
            create_constraint=True,
            length=24,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    sets: Mapped[int] = mapped_column(Integer, nullable=False)
    rep_min: Mapped[int | None] = mapped_column(Integer)
    rep_max: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    distance_meters: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    rounds_target: Mapped[int | None] = mapped_column(Integer)
    rest_seconds: Mapped[int | None] = mapped_column(Integer)
    target_rir: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    superset_group: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)
    optional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    split_day: Mapped[SplitDay] = relationship(back_populates="items")
    exercise: Mapped[Exercise] = relationship(back_populates="template_items")
    alternatives: Mapped[list[TemplateAlternative]] = relationship(
        back_populates="template_item",
        cascade="all, delete-orphan",
        order_by="TemplateAlternative.sequence",
    )


class TemplateAlternative(Base):
    __tablename__ = "template_alternatives"

    template_item_id: Mapped[str] = mapped_column(
        ForeignKey("workout_template_items.id", ondelete="CASCADE"), primary_key=True
    )
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"), primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    template_item: Mapped[WorkoutTemplateItem] = relationship(back_populates="alternatives")
    exercise: Mapped[Exercise] = relationship(back_populates="alternatives")


class WorkoutSession(IdMixin, TimestampMixin, Base):
    __tablename__ = "workout_sessions"
    __table_args__ = (
        CheckConstraint(
            "perceived_effort IS NULL OR perceived_effort BETWEEN 1 AND 10",
            name="ck_workout_sessions_effort",
        ),
        Index("idx_workout_sessions_date_status", "user_id", "session_date_local", "status"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    split_day_id: Mapped[str | None] = mapped_column(ForeignKey("split_days.id"))
    session_date_local: Mapped[date] = mapped_column(nullable=False)
    started_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None]
    status: Mapped[SessionStatus] = mapped_column(
        Enum(
            SessionStatus,
            native_enum=False,
            create_constraint=True,
            length=20,
            values_callable=enum_values,
        ),
        default=SessionStatus.IN_PROGRESS,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    public_visibility: Mapped[PublicVisibility] = mapped_column(
        Enum(
            PublicVisibility,
            native_enum=False,
            create_constraint=True,
            length=16,
            values_callable=enum_values,
        ),
        default=PublicVisibility.PRIVATE,
        nullable=False,
    )
    perceived_effort: Mapped[int | None] = mapped_column(Integer)
    notes_private: Mapped[str | None] = mapped_column(Text)
    notes_public: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime | None]
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True)

    split_day: Mapped[SplitDay | None] = relationship(back_populates="sessions")
    exercises: Mapped[list[SessionExercise]] = relationship(
        back_populates="workout_session",
        cascade="all, delete-orphan",
        order_by="SessionExercise.sequence",
    )


class SessionExercise(IdMixin, Base):
    __tablename__ = "session_exercises"
    __table_args__ = (
        UniqueConstraint(
            "workout_session_id", "sequence", name="uq_session_exercises_session_sequence"
        ),
        Index("idx_session_exercises_session_sequence", "workout_session_id", "sequence"),
    )

    workout_session_id: Mapped[str] = mapped_column(
        ForeignKey("workout_sessions.id", ondelete="CASCADE")
    )
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"))
    source_template_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("workout_template_items.id")
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    planned_sets: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    item_type: Mapped[TemplateItemType] = mapped_column(
        Enum(
            TemplateItemType,
            native_enum=False,
            create_constraint=True,
            length=24,
            values_callable=enum_values,
        ),
        default=TemplateItemType.ACCESSORY,
        nullable=False,
    )
    display_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    variation_group_snapshot: Mapped[str] = mapped_column(String(150), nullable=False)
    rep_min_snapshot: Mapped[int | None] = mapped_column(Integer)
    rep_max_snapshot: Mapped[int | None] = mapped_column(Integer)
    duration_seconds_snapshot: Mapped[int | None] = mapped_column(Integer)
    distance_meters_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    rounds_target_snapshot: Mapped[int | None] = mapped_column(Integer)
    rest_seconds_snapshot: Mapped[int | None] = mapped_column(Integer)
    target_rir_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    optional_snapshot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    substitution_reason: Mapped[str | None] = mapped_column(Text)
    removed_at: Mapped[datetime | None]
    removal_reason: Mapped[str | None] = mapped_column(String(300))

    workout_session: Mapped[WorkoutSession] = relationship(back_populates="exercises")
    exercise: Mapped[Exercise] = relationship(back_populates="session_exercises")
    sets: Mapped[list[SetLog]] = relationship(
        back_populates="session_exercise",
        cascade="all, delete-orphan",
        order_by="SetLog.sequence",
    )


class SetLog(IdMixin, Base):
    __tablename__ = "set_logs"
    __table_args__ = (
        CheckConstraint("load_kg IS NULL OR load_kg >= 0", name="ck_set_logs_load"),
        CheckConstraint("reps IS NULL OR reps BETWEEN 0 AND 100", name="ck_set_logs_reps"),
        CheckConstraint("rir IS NULL OR rir BETWEEN 0 AND 10", name="ck_set_logs_rir"),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0", name="ck_set_logs_duration"
        ),
        CheckConstraint(
            "distance_meters IS NULL OR distance_meters >= 0", name="ck_set_logs_distance"
        ),
        CheckConstraint("rounds IS NULL OR rounds >= 0", name="ck_set_logs_rounds"),
        CheckConstraint(
            "form_quality IS NULL OR form_quality BETWEEN 1 AND 5",
            name="ck_set_logs_form_quality",
        ),
        UniqueConstraint("session_exercise_id", "sequence", name="uq_set_logs_exercise_sequence"),
        Index("idx_set_logs_session_exercise_sequence", "session_exercise_id", "sequence"),
    )

    session_exercise_id: Mapped[str] = mapped_column(
        ForeignKey("session_exercises.id", ondelete="CASCADE")
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    set_type: Mapped[SetType] = mapped_column(
        Enum(
            SetType,
            native_enum=False,
            create_constraint=True,
            length=16,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    load_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    reps: Mapped[int | None] = mapped_column(Integer)
    rir: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    distance_meters: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    rounds: Mapped[int | None] = mapped_column(Integer)
    bodyweight_assistance_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    form_quality: Mapped[int | None] = mapped_column(Integer)
    pain_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime | None]
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True)

    session_exercise: Mapped[SessionExercise] = relationship(back_populates="sets")
    records: Mapped[list[PersonalRecord]] = relationship(back_populates="set_log")
    achievements: Mapped[list[Achievement]] = relationship(back_populates="set_log")


class ReadinessLog(IdMixin, TimestampMixin, Base):
    __tablename__ = "readiness_logs"
    __table_args__ = (
        CheckConstraint("energy BETWEEN 1 AND 5", name="ck_readiness_energy"),
        CheckConstraint("soreness BETWEEN 1 AND 5", name="ck_readiness_soreness"),
        CheckConstraint("sleep_quality BETWEEN 1 AND 5", name="ck_readiness_sleep"),
        UniqueConstraint("user_id", "local_date", name="uq_readiness_user_date"),
        Index("idx_readiness_user_date", "user_id", "local_date"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    local_date: Mapped[date] = mapped_column(nullable=False)
    energy: Mapped[int] = mapped_column(Integer, nullable=False)
    soreness: Mapped[int] = mapped_column(Integer, nullable=False)
    sleep_quality: Mapped[int] = mapped_column(Integer, nullable=False)
    pain_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note_private: Mapped[str | None] = mapped_column(Text)


class WaterLog(IdMixin, Base):
    __tablename__ = "water_logs"
    __table_args__ = (
        CheckConstraint("amount_ml BETWEEN 1 AND 5000", name="ck_water_logs_amount"),
        Index("idx_water_logs_local_date", "user_id", "local_date"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    occurred_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    local_date: Mapped[date] = mapped_column(nullable=False)
    amount_ml: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[WaterSource] = mapped_column(
        Enum(
            WaterSource,
            native_enum=False,
            create_constraint=True,
            length=16,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True)
