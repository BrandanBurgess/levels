from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from levels_api.errors import ApiError
from levels_api.models import AvatarSettings, BasePresentation

ALLOWED_VALUES: dict[str, set[str]] = {
    "base_presentation": {member.value for member in BasePresentation},
    "skin_tone": {"deep", "rich", "medium_deep", "medium", "light_medium", "light"},
    "hairstyle": {
        "short_coils",
        "fade",
        "waves",
        "locs",
        "short_locs",
        "braids",
        "bun",
        "bob",
        "curly_bob",
        "long_curls",
        "short_straight",
        "covered",
        "bald",
    },
    "hair_color": {"black", "dark_brown", "brown", "auburn", "gray", "blonde"},
    "outfit_style": {
        "training_tee",
        "tank_and_shorts",
        "long_sleeve",
        "modest_activewear",
    },
    "outfit_palette": {"violet", "teal", "blue", "rose", "neutral"},
    "accessory": {"none", "glasses", "headband", "wristbands", "cap"},
    "background": {"none", "gradient", "gym", "dusk"},
    "aura_style": {"standard", "rings", "sparks"},
}
ALLOWED_FIELDS = set(ALLOWED_VALUES) | {"aura_enabled"}


def get_avatar(session: Session, user_id: str) -> AvatarSettings:
    avatar = session.get(AvatarSettings, user_id)
    if avatar is None:
        avatar = AvatarSettings(user_id=user_id)
        session.add(avatar)
        session.flush()
    return avatar


def update_avatar(session: Session, user_id: str, values: dict[str, Any]) -> AvatarSettings:
    unexpected = set(values) - ALLOWED_FIELDS
    field_errors: dict[str, str] = {}
    if unexpected:
        field_errors["body"] = "Unexpected fields are not allowed."
    for field, allowed in ALLOWED_VALUES.items():
        if field in values and values[field] not in allowed:
            field_errors[field] = "Value is not supported."
    if "aura_enabled" in values and not isinstance(values["aura_enabled"], bool):
        field_errors["aura_enabled"] = "Must be a boolean."
    if field_errors:
        raise ApiError(422, "VALIDATION_ERROR", "One or more fields are invalid.", field_errors)

    avatar = get_avatar(session, user_id)
    for field, value in values.items():
        if field == "base_presentation":
            value = BasePresentation(value)
        setattr(avatar, field, value)
    session.flush()
    return avatar


def serialize_avatar(avatar: AvatarSettings) -> dict[str, str | bool]:
    return {
        "base_presentation": avatar.base_presentation.value,
        "skin_tone": avatar.skin_tone,
        "hairstyle": avatar.hairstyle,
        "hair_color": avatar.hair_color,
        "outfit_style": avatar.outfit_style,
        "outfit_palette": avatar.outfit_palette,
        "accessory": avatar.accessory,
        "background": avatar.background,
        "aura_style": avatar.aura_style,
        "aura_enabled": avatar.aura_enabled,
    }
