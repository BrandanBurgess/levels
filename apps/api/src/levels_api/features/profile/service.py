from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from levels_api.errors import ApiError
from levels_api.models import Profile

from . import repository
from .schemas import ProfileUpdate, SettingsUpdate


def require_profile(session: Session) -> Profile:
    profile = repository.get_profile(session)
    if profile is None or profile.settings is None or profile.visibility is None:
        raise ApiError(503, "DATA_NOT_INITIALIZED", "Profile data is unavailable.")
    return profile


def update_profile(session: Session, profile: Profile, update: ProfileUpdate) -> None:
    fields = update.model_fields_set
    if "display_name" in fields:
        if update.display_name is None:
            raise ApiError(400, "VALIDATION_ERROR", "Display name cannot be null.")
        profile.display_name = update.display_name
    if "height_cm" in fields:
        profile.height_cm = update.height_cm
    if "body_weight_kg" in fields:
        profile.body_weight_kg = update.body_weight_kg
    if "preferred_units" in fields:
        if update.preferred_units is None:
            raise ApiError(400, "VALIDATION_ERROR", "Preferred units cannot be null.")
        profile.preferred_units = update.preferred_units
    if "timezone" in fields:
        if update.timezone is None:
            raise ApiError(400, "VALIDATION_ERROR", "Timezone cannot be null.")
        try:
            ZoneInfo(update.timezone)
        except ZoneInfoNotFoundError as error:
            raise ApiError(
                400,
                "VALIDATION_ERROR",
                "One or more fields are invalid.",
                {"timezone": "Must be a valid IANA timezone."},
            ) from error
        profile.timezone = update.timezone


def update_settings(session: Session, profile: Profile, update: SettingsUpdate) -> None:
    settings = profile.settings
    visibility = profile.visibility
    assert settings is not None and visibility is not None
    fields = update.model_fields_set
    if "active_split_id" in fields:
        if update.active_split_id is not None and not repository.split_exists(
            session, update.active_split_id
        ):
            raise ApiError(
                400,
                "VALIDATION_ERROR",
                "One or more fields are invalid.",
                {"active_split_id": "Split does not exist."},
            )
        settings.active_split_id = update.active_split_id
    for field in (
        "week_starts_on",
        "default_water_goal_ml",
        "water_quick_add_ml",
        "default_target_rir",
        "default_load_increment_kg",
    ):
        if field in fields:
            value = getattr(update, field)
            if value is None:
                raise ApiError(400, "VALIDATION_ERROR", f"{field} cannot be null.")
            setattr(settings, field, value)
    if "reduced_motion_override" in fields:
        settings.reduced_motion_override = update.reduced_motion_override
    if "visibility" in fields:
        if update.visibility is None:
            raise ApiError(400, "VALIDATION_ERROR", "Visibility cannot be null.")
        for field in update.visibility.model_fields_set:
            value = getattr(update.visibility, field)
            if value is None:
                raise ApiError(400, "VALIDATION_ERROR", f"{field} cannot be null.")
            setattr(visibility, field, value)
