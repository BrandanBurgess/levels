from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, jsonify, request
from pydantic import ValidationError

from levels_api.auth import current_user_id, require_user
from levels_api.database import get_db, transaction
from levels_api.errors import ApiError

from .schemas import SplitWrite
from .service import (
    activate_split,
    archive_split,
    create_split,
    list_splits,
    require_split,
    serialize_split,
    update_split,
)

split_blueprint = Blueprint("splits", __name__, url_prefix="/api/v1")


def _write() -> SplitWrite:
    payload: Any = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError(400, "VALIDATION_ERROR", "A JSON request body is required.")
    try:
        return SplitWrite.model_validate(payload)
    except ValidationError as error:
        fields = {
            ".".join(str(part) for part in item["loc"]): str(item["msg"]) for item in error.errors()
        }
        raise ApiError(
            400, "VALIDATION_ERROR", "One or more fields are invalid.", fields
        ) from error


@split_blueprint.get("/splits")
@require_user
def get_splits() -> tuple[Response, int]:
    return jsonify(list_splits(get_db(), current_user_id())), 200


@split_blueprint.post("/splits")
@require_user
def post_split() -> tuple[Response, int]:
    user_id = current_user_id()
    with transaction() as session:
        result = serialize_split(create_split(session, user_id, _write()), user_id)
    return jsonify(result), 201


@split_blueprint.get("/splits/<split_id>")
@require_user
def get_split(split_id: str) -> tuple[Response, int]:
    user_id = current_user_id()
    return jsonify(serialize_split(require_split(get_db(), user_id, split_id), user_id)), 200


@split_blueprint.patch("/splits/<split_id>")
@require_user
def patch_split(split_id: str) -> tuple[Response, int]:
    user_id = current_user_id()
    with transaction() as session:
        result = serialize_split(update_split(session, user_id, split_id, _write()), user_id)
    return jsonify(result), 200


@split_blueprint.delete("/splits/<split_id>")
@require_user
def delete_split(split_id: str) -> tuple[str, int]:
    user_id = current_user_id()
    with transaction() as session:
        archive_split(session, user_id, split_id)
    return "", 204


@split_blueprint.post("/splits/<split_id>/activate")
@require_user
def post_activate_split(split_id: str) -> tuple[Response, int]:
    user_id = current_user_id()
    with transaction() as session:
        result = serialize_split(activate_split(session, user_id, split_id), user_id)
    return jsonify(result), 200
