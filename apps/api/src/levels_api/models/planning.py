from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IdMixin, TimestampMixin
from .enums import (
    BasePresentation,
    OverrideAction,
    ScheduleEffect,
    TemplateItemType,
    enum_values,
)


class ScheduleState(TimestampMixin, Base):
    __tablename__ = "schedule_state"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    active_split_id: Mapped[str | None] = mapped_column(ForeignKey("splits.id"))
    cursor_split_day_id: Mapped[str | None] = mapped_column(ForeignKey("split_days.id"))
    cursor_effective_date: Mapped[date | None]
    version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class DailyPlanOverride(IdMixin, TimestampMixin, Base):
    __tablename__ = "daily_plan_overrides"
    __table_args__ = (
        UniqueConstraint("user_id", "local_date", name="uq_daily_override_user_date"),
        Index("idx_daily_override_user_date", "user_id", "local_date"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    local_date: Mapped[date] = mapped_column(nullable=False)
    action: Mapped[OverrideAction] = mapped_column(
        Enum(
            OverrideAction,
            native_enum=False,
            create_constraint=True,
            length=16,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    planned_split_day_id: Mapped[str | None] = mapped_column(ForeignKey("split_days.id"))
    effective_split_day_id: Mapped[str | None] = mapped_column(ForeignKey("split_days.id"))
    swap_target_local_date: Mapped[date | None]
    schedule_effect: Mapped[ScheduleEffect] = mapped_column(
        Enum(
            ScheduleEffect,
            native_enum=False,
            create_constraint=True,
            length=24,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(String(300))
    swap_group_id: Mapped[str | None] = mapped_column(String(36), index=True)
    version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class DailyExercisePlan(IdMixin, TimestampMixin, Base):
    __tablename__ = "daily_exercise_plans"
    __table_args__ = (
        UniqueConstraint("user_id", "local_date", name="uq_daily_exercise_plan_user_date"),
        Index("idx_daily_exercise_plan_user_date", "user_id", "local_date"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    local_date: Mapped[date] = mapped_column(nullable=False)
    source_split_day_id: Mapped[str | None] = mapped_column(ForeignKey("split_days.id"))
    version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class DailyExercisePlanItem(IdMixin, Base):
    __tablename__ = "daily_exercise_plan_items"
    __table_args__ = (
        UniqueConstraint("daily_exercise_plan_id", "sequence", name="uq_daily_item_sequence"),
        Index("idx_daily_item_plan_sequence", "daily_exercise_plan_id", "sequence"),
    )

    daily_exercise_plan_id: Mapped[str] = mapped_column(
        ForeignKey("daily_exercise_plans.id", ondelete="CASCADE")
    )
    source_template_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("workout_template_items.id")
    )
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
        default=TemplateItemType.ACCESSORY,
        nullable=False,
    )
    planned_sets: Mapped[int] = mapped_column(Integer, nullable=False)
    rep_min: Mapped[int | None]
    rep_max: Mapped[int | None]
    duration_seconds: Mapped[int | None]
    distance_meters: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    rounds_target: Mapped[int | None]
    rest_seconds: Mapped[int | None]
    target_rir: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    superset_group: Mapped[str | None] = mapped_column(String(50))
    optional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class AvatarSettings(TimestampMixin, Base):
    __tablename__ = "avatar_settings"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    base_presentation: Mapped[BasePresentation] = mapped_column(
        Enum(
            BasePresentation,
            native_enum=False,
            create_constraint=True,
            length=16,
            values_callable=enum_values,
        ),
        default=BasePresentation.MALE,
        nullable=False,
    )
    skin_tone: Mapped[str] = mapped_column(String(32), default="rich", nullable=False)
    hairstyle: Mapped[str] = mapped_column(String(32), default="short_coils", nullable=False)
    hair_color: Mapped[str] = mapped_column(String(32), default="black", nullable=False)
    outfit_style: Mapped[str] = mapped_column(String(32), default="training_tee", nullable=False)
    outfit_palette: Mapped[str] = mapped_column(String(32), default="violet", nullable=False)
    accessory: Mapped[str] = mapped_column(String(32), default="none", nullable=False)
    background: Mapped[str] = mapped_column(String(32), default="gradient", nullable=False)
    aura_style: Mapped[str] = mapped_column(String(32), default="standard", nullable=False)
    aura_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CommandReceipt(IdMixin, TimestampMixin, Base):
    __tablename__ = "command_receipts"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "operation", "idempotency_key", name="uq_command_receipt_actor_operation_key"
        ),
        Index("idx_command_receipt_actor_created", "user_id", "created_at"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    operation: Mapped[str] = mapped_column(String(80), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_resource_id: Mapped[str | None] = mapped_column(String(36))
    result_version: Mapped[int | None]
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
