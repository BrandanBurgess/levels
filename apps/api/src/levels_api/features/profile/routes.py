from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, jsonify, request
from pydantic import BaseModel, ValidationError

from levels_api.auth import require_admin
from levels_api.database import get_db, transaction
from levels_api.errors import ApiError
from levels_api.schemas import (
    serialize_admin_profile,
    serialize_public_profile,
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


@profile_blueprint.get("/public/profile")
def public_profile() -> tuple[Response, int]:
    return jsonify(serialize_public_profile(require_profile(get_db()))), 200


@profile_blueprint.get("/profile")
@require_admin
def owner_profile() -> tuple[Response, int]:
    return jsonify(serialize_admin_profile(require_profile(get_db()))), 200


@profile_blueprint.patch("/profile")
@require_admin
def patch_profile() -> tuple[Response, int]:
    update = _parse(ProfileUpdate)
    with transaction() as session:
        profile = require_profile(session)
        update_profile(session, profile, update)
        session.flush()
        result = serialize_admin_profile(profile)
    return jsonify(result), 200


@profile_blueprint.get("/settings")
@require_admin
def owner_settings() -> tuple[Response, int]:
    return jsonify(serialize_settings(require_profile(get_db()))), 200


@profile_blueprint.patch("/settings")
@require_admin
def patch_settings() -> tuple[Response, int]:
    update = _parse(SettingsUpdate)
    with transaction() as session:
        profile = require_profile(session)
        update_settings(session, profile, update)
        session.flush()
        result = serialize_settings(profile)
    return jsonify(result), 200
