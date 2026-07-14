from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Enum, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IdMixin, utc_now
from .enums import RecordType, SuggestionConfidence, enum_values

if TYPE_CHECKING:
    from .catalog import Exercise
    from .training import SetLog


class PersonalRecord(IdMixin, Base):
    __tablename__ = "personal_records"
    __table_args__ = (
        Index("idx_personal_records_current", "exercise_id", "record_type", "is_current"),
    )

    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"), nullable=False)
    record_type: Mapped[RecordType] = mapped_column(
        Enum(
            RecordType,
            native_enum=False,
            create_constraint=True,
            length=24,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    value_numeric: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    reps_context: Mapped[int | None] = mapped_column(Integer)
    set_log_id: Mapped[str | None] = mapped_column(ForeignKey("set_logs.id"))
    achieved_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    exercise: Mapped[Exercise] = relationship()
    set_log: Mapped[SetLog | None] = relationship(back_populates="records")


class Achievement(IdMixin, Base):
    __tablename__ = "achievements"

    achievement_type: Mapped[str] = mapped_column(String(50), nullable=False)
    exercise_id: Mapped[str | None] = mapped_column(ForeignKey("exercises.id"))
    set_log_id: Mapped[str | None] = mapped_column(ForeignKey("set_logs.id"))
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    achieved_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)

    exercise: Mapped[Exercise | None] = relationship()
    set_log: Mapped[SetLog | None] = relationship(back_populates="achievements")


class ProgressionSuggestion(IdMixin, Base):
    __tablename__ = "progression_suggestions"

    local_date: Mapped[date] = mapped_column(nullable=False)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"), nullable=False)
    suggestion_type: Mapped[str] = mapped_column(String(50), nullable=False)
    suggested_delta: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    confidence: Mapped[SuggestionConfidence] = mapped_column(
        Enum(
            SuggestionConfidence,
            native_enum=False,
            create_constraint=True,
            length=16,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    explanation_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    source_session_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    accepted_at: Mapped[datetime | None]
    dismissed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    exercise: Mapped[Exercise] = relationship()
