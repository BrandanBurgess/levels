from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, CheckConstraint, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IdMixin, TimestampMixin
from .enums import PreferredUnits, enum_values

if TYPE_CHECKING:
    from .training import Split


class Profile(IdMixin, TimestampMixin, Base):
    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint(
            "height_cm IS NULL OR height_cm BETWEEN 100 AND 250",
            name="ck_profiles_height_cm",
        ),
        CheckConstraint(
            "body_weight_kg IS NULL OR body_weight_kg BETWEEN 20 AND 400",
            name="ck_profiles_body_weight_kg",
        ),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    height_cm: Mapped[int | None] = mapped_column(Integer)
    body_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(7, 3))
    preferred_units: Mapped[PreferredUnits] = mapped_column(
        Enum(
            PreferredUnits,
            native_enum=False,
            create_constraint=True,
            length=16,
            values_callable=enum_values,
        ),
        default=PreferredUnits.IMPERIAL,
        nullable=False,
    )
    timezone: Mapped[str] = mapped_column(String(100), default="America/Toronto", nullable=False)
    avatar_variant: Mapped[str] = mapped_column(
        String(100), default="brandan-original-v1", nullable=False
    )

    visibility: Mapped[VisibilitySettings] = relationship(
        back_populates="profile", cascade="all, delete-orphan", uselist=False
    )
    settings: Mapped[AppSettings] = relationship(
        back_populates="profile", cascade="all, delete-orphan", uselist=False
    )


class VisibilitySettings(IdMixin, Base):
    __tablename__ = "visibility_settings"

    profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    show_height: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_body_weight: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    show_water: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    show_session_summaries: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_set_details: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    show_public_notes: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    show_progress_charts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_personal_records: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_readiness: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    profile: Mapped[Profile] = relationship(back_populates="visibility")


class AppSettings(IdMixin, TimestampMixin, Base):
    __tablename__ = "app_settings"
    __table_args__ = (
        CheckConstraint("week_starts_on BETWEEN 0 AND 6", name="ck_app_settings_week_start"),
        CheckConstraint(
            "default_water_goal_ml BETWEEN 250 AND 10000",
            name="ck_app_settings_water_goal",
        ),
        CheckConstraint("default_target_rir BETWEEN 0 AND 10", name="ck_app_settings_target_rir"),
        CheckConstraint("default_load_increment_kg > 0", name="ck_app_settings_load_increment"),
        CheckConstraint(
            "primary_muscle_weight >= 0 AND secondary_muscle_weight >= 0",
            name="ck_app_settings_muscle_weights",
        ),
    )

    profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    active_split_id: Mapped[str | None] = mapped_column(ForeignKey("splits.id"))
    week_starts_on: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    default_water_goal_ml: Mapped[int] = mapped_column(Integer, default=2800, nullable=False)
    water_quick_add_ml: Mapped[list[int]] = mapped_column(
        JSON, default=lambda: [250, 500, 750], nullable=False
    )
    primary_muscle_weight: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), default=Decimal("1.0"), nullable=False
    )
    secondary_muscle_weight: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), default=Decimal("0.45"), nullable=False
    )
    default_target_rir: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), default=Decimal("2.0"), nullable=False
    )
    default_load_increment_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), default=Decimal("1.133981"), nullable=False
    )
    reduced_motion_override: Mapped[bool | None] = mapped_column(Boolean)

    profile: Mapped[Profile] = relationship(back_populates="settings")
    active_split: Mapped[Split | None] = relationship(foreign_keys=[active_split_id])
