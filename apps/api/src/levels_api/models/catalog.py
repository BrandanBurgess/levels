from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IdMixin, TimestampMixin
from .enums import MeasurementType, MuscleRole, enum_values

if TYPE_CHECKING:
    from .training import SessionExercise, TemplateAlternative, WorkoutTemplateItem


class MuscleGroup(IdMixin, Base):
    __tablename__ = "muscle_groups"

    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    body_region: Mapped[str] = mapped_column(String(50), nullable=False)
    svg_region_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    highlightable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    exercise_links: Mapped[list[ExerciseMuscle]] = relationship(
        back_populates="muscle_group", cascade="all, delete-orphan"
    )


class Exercise(IdMixin, TimestampMixin, Base):
    __tablename__ = "exercises"
    __table_args__ = (
        CheckConstraint(
            "default_rep_min IS NULL OR default_rep_min >= 0", name="ck_exercises_rep_min"
        ),
        CheckConstraint(
            "default_rep_max IS NULL OR default_rep_max >= default_rep_min",
            name="ck_exercises_rep_max",
        ),
        Index("idx_exercises_variation_group", "variation_group"),
        Index("idx_exercises_owner_archived", "owner_user_id", "archived_at"),
        Index(
            "uq_global_exercises_slug",
            "slug",
            unique=True,
            sqlite_where=text("owner_user_id IS NULL"),
        ),
        Index(
            "uq_custom_exercises_owner_slug",
            "owner_user_id",
            "slug",
            unique=True,
            sqlite_where=text("owner_user_id IS NOT NULL"),
        ),
    )

    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    slug: Mapped[str] = mapped_column(String(150), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    variation_group: Mapped[str] = mapped_column(String(150), nullable=False)
    movement_pattern: Mapped[str] = mapped_column(String(50), nullable=False)
    equipment: Mapped[str] = mapped_column(String(50), nullable=False)
    measurement_type: Mapped[MeasurementType] = mapped_column(
        Enum(
            MeasurementType,
            native_enum=False,
            create_constraint=True,
            length=24,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    compound: Mapped[bool] = mapped_column(Boolean, nullable=False)
    unilateral: Mapped[bool] = mapped_column(Boolean, nullable=False)
    default_rep_min: Mapped[int | None] = mapped_column(Integer)
    default_rep_max: Mapped[int | None] = mapped_column(Integer)
    default_rest_seconds: Mapped[int | None] = mapped_column(Integer)
    progression_increment_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    automatic_progression_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    archived_at: Mapped[datetime | None]

    muscle_links: Mapped[list[ExerciseMuscle]] = relationship(
        back_populates="exercise", cascade="all, delete-orphan"
    )
    template_items: Mapped[list[WorkoutTemplateItem]] = relationship(back_populates="exercise")
    alternatives: Mapped[list[TemplateAlternative]] = relationship(back_populates="exercise")
    session_exercises: Mapped[list[SessionExercise]] = relationship(back_populates="exercise")


class ExerciseMuscle(Base):
    __tablename__ = "exercise_muscles"
    __table_args__ = (
        CheckConstraint("contribution BETWEEN 0 AND 1", name="ck_exercise_muscles_contribution"),
        Index("idx_exercise_muscles_exercise", "exercise_id"),
    )

    exercise_id: Mapped[str] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True
    )
    muscle_group_id: Mapped[str] = mapped_column(
        ForeignKey("muscle_groups.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[MuscleRole] = mapped_column(
        Enum(
            MuscleRole,
            native_enum=False,
            create_constraint=True,
            length=16,
            values_callable=enum_values,
        ),
        primary_key=True,
    )
    contribution: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)

    exercise: Mapped[Exercise] = relationship(back_populates="muscle_links")
    muscle_group: Mapped[MuscleGroup] = relationship(back_populates="exercise_links")
