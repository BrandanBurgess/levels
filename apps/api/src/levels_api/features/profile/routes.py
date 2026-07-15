from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, jsonify, request
from pydantic import BaseModel, ValidationError

from levels_api.auth import current_user_id, require_user
from levels_api.database import get_db, transaction
from levels_api.errors import ApiError
from levels_api.schemas import (
    serialize_admin_profile,
    serialize_settings,
)

from .schemas import ProfileUpdate, SettingsUpdate
from .service import require_profile, update_profile, update_settings

profile_blueprint = Blueprint("profile", __name__, url_prefix="/api/v1")


def _parse[RequestModel: BaseModel](model: type[RequestModel]) -> RequestModel:
    payload: Any = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError(400, "VALIDATION_ERROR", "A JSON request body is required.")
    try:
        return model.model_validate(payload)
    except ValidationError as error:
        field_errors = {
            ".".join(str(part) for part in item["loc"]): str(item["msg"]) for item in error.errors()
        }
        raise ApiError(
            400, "VALIDATION_ERROR", "One or more fields are invalid.", field_errors
        ) from error


@profile_blueprint.get("/me/profile")
@require_user
def owner_profile() -> tuple[Response, int]:
    payload = serialize_admin_profile(require_profile(get_db(), current_user_id()))
    payload.pop("avatar_variant", None)
    return jsonify(payload), 200


@profile_blueprint.patch("/me/profile")
@require_user
def patch_profile() -> tuple[Response, int]:
    user_id = current_user_id()
    update = _parse(ProfileUpdate)
    with transaction() as session:
        profile = require_profile(session, user_id)
        update_profile(session, profile, update)
        session.flush()
        result = serialize_admin_profile(profile)
        result.pop("avatar_variant", None)
    return jsonify(result), 200


@profile_blueprint.get("/settings")
@require_user
def owner_settings() -> tuple[Response, int]:
    return jsonify(serialize_settings(require_profile(get_db(), current_user_id()))), 200


@profile_blueprint.patch("/settings")
@require_user
def patch_settings() -> tuple[Response, int]:
    user_id = current_user_id()
    update = _parse(SettingsUpdate)
    with transaction() as session:
        profile = require_profile(session, user_id)
        update_settings(session, user_id, profile, update)
        session.flush()
        result = serialize_settings(profile)
    return jsonify(result), 200
