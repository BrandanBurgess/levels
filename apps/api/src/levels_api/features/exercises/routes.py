from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, jsonify, request
from pydantic import ValidationError

from levels_api.auth import current_user_id, require_user
from levels_api.database import get_db, transaction
from levels_api.errors import ApiError

from .schemas import ExerciseWrite
from .service import (
    archive_exercise,
    create_exercise,
    list_muscle_groups,
    require_exercise,
    search_exercises,
    serialize_exercise,
    update_exercise,
)

exercise_blueprint = Blueprint("exercises", __name__, url_prefix="/api/v1")


def _write() -> ExerciseWrite:
    payload: Any = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError(400, "VALIDATION_ERROR", "A JSON request body is required.")
    try:
        return ExerciseWrite.model_validate(payload)
    except ValidationError as error:
        fields = {
            ".".join(str(part) for part in item["loc"]): str(item["msg"]) for item in error.errors()
        }
        raise ApiError(
            400, "VALIDATION_ERROR", "One or more fields are invalid.", fields
        ) from error


@exercise_blueprint.get("/exercises")
@require_user
def list_exercises() -> tuple[Response, int]:
    scope = request.args.get("scope", "available")
    if scope not in {"available", "global", "mine"}:
        raise ApiError(400, "VALIDATION_ERROR", "scope must be available, global, or mine.")
    result = search_exercises(
        get_db(),
        current_user_id(),
        scope=scope,
        query=request.args.get("search"),
        muscle_id=request.args.get("muscle_id"),
        movement_pattern=request.args.get("movement_pattern"),
        equipment=request.args.get("equipment"),
        measurement_type=request.args.get("measurement_type"),
    )
    return jsonify(result), 200


@exercise_blueprint.post("/exercises")
@require_user
def post_exercise() -> tuple[Response, int]:
    user_id = current_user_id()
    with transaction() as session:
        result = serialize_exercise(create_exercise(session, user_id, _write()), user_id)
    return jsonify(result), 201


@exercise_blueprint.get("/exercises/<exercise_id>")
@require_user
def get_exercise(exercise_id: str) -> tuple[Response, int]:
    user_id = current_user_id()
    exercise = require_exercise(get_db(), user_id, exercise_id)
    return jsonify(serialize_exercise(exercise, user_id)), 200


@exercise_blueprint.patch("/exercises/<exercise_id>")
@require_user
def patch_exercise(exercise_id: str) -> tuple[Response, int]:
    user_id = current_user_id()
    with transaction() as session:
        result = serialize_exercise(
            update_exercise(session, user_id, exercise_id, _write()), user_id
        )
    return jsonify(result), 200


@exercise_blueprint.delete("/exercises/<exercise_id>")
@require_user
def delete_exercise(exercise_id: str) -> tuple[str, int]:
    user_id = current_user_id()
    with transaction() as session:
        archive_exercise(session, user_id, exercise_id)
    return "", 204


@exercise_blueprint.get("/muscles")
@require_user
def get_muscles() -> tuple[Response, int]:
    return jsonify(list_muscle_groups(get_db())), 200
