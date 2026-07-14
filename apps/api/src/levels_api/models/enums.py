from enum import Enum, StrEnum


def enum_values(enum_class: type[Enum]) -> list[str]:
    """Persist string enum values instead of Python member names."""
    return [str(member.value) for member in enum_class]


class PreferredUnits(StrEnum):
    IMPERIAL = "imperial"
    METRIC = "metric"


class MuscleRole(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    STABILIZER = "stabilizer"


class MeasurementType(StrEnum):
    LOAD_REPS = "load_reps"
    BODYWEIGHT_REPS = "bodyweight_reps"
    DURATION = "duration"
    DISTANCE = "distance"
    ROUNDS = "rounds"


class TemplateItemType(StrEnum):
    ACTIVATION = "activation"
    POWER = "power"
    MAIN = "main"
    ACCESSORY = "accessory"
    CORE = "core"
    CONDITIONING = "conditioning"


class SessionStatus(StrEnum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PublicVisibility(StrEnum):
    PRIVATE = "private"
    SUMMARY = "summary"
    FULL = "full"


class SetType(StrEnum):
    WARMUP = "warmup"
    WORKING = "working"
    BACKOFF = "backoff"
    DROP = "drop"
    FAILURE = "failure"


class WaterSource(StrEnum):
    QUICK_ADD = "quick_add"
    CUSTOM = "custom"
    CORRECTION = "correction"


class RecordType(StrEnum):
    MAX_LOAD = "max_load"
    REPS_AT_LOAD = "reps_at_load"
    ESTIMATED_1RM = "estimated_1rm"
    SESSION_VOLUME = "session_volume"
    DURATION = "duration"
    DISTANCE = "distance"
    ROUNDS = "rounds"


class SuggestionConfidence(StrEnum):
    INSUFFICIENT = "insufficient"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
