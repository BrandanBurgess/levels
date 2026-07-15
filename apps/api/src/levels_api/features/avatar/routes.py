from __future__ import annotations

from typing import Any, cast

from flask import Blueprint, Response, jsonify, request

from levels_api.auth import current_user_id, require_user
from levels_api.database import get_db, transaction
from levels_api.errors import ApiError

from .service import get_avatar, serialize_avatar, update_avatar

avatar_blueprint = Blueprint("avatar", __name__, url_prefix="/api/v1/me/avatar")


@avatar_blueprint.get("")
@require_user
def read_avatar() -> Response:
    avatar = get_avatar(get_db(), current_user_id())
    get_db().commit()
    return jsonify(serialize_avatar(avatar))


@avatar_blueprint.patch("")
@require_user
def patch_avatar() -> Response:
    payload: Any = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError(422, "VALIDATION_ERROR", "A JSON request body is required.")
    with transaction() as session:
        avatar = update_avatar(session, current_user_id(), cast(dict[str, Any], payload))
        response = serialize_avatar(avatar)
    return jsonify(response)
