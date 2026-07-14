from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, jsonify, request
from pydantic import ValidationError

from levels_api.auth import require_admin
from levels_api.database import get_db, transaction
from levels_api.errors import ApiError

from .schemas import ExerciseWrite
from .service import (
    archive_exercise,
    create_exercise,
    require_exercise,
    search_exercises,
    serialize_exercise,
    update_exercise,
)

exercise_blueprint = Blueprint("exercises", __name__, url_prefix="/api/v1")


def _boolean(name: str) -> bool | None:
    value = request.args.get(name)
    if value is None:
        return None
    if value.lower() in {"true", "1"}:
        return True
    if value.lower() in {"false", "0"}:
        return False
    raise ApiError(
        400, "VALIDATION_ERROR", f"{name} must be true or false.", {name: "Invalid boolean"}
    )


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
def list_exercises() -> tuple[Response, int]:
    result = search_exercises(
        get_db(),
        query=request.args.get("q"),
        primary_muscle=request.args.get("primary_muscle"),
        secondary_muscle=request.args.get("secondary_muscle"),
        body_region=request.args.get("body_region"),
        movement_pattern=request.args.get("movement_pattern"),
        equipment=request.args.get("equipment"),
        unilateral=_boolean("unilateral"),
        include_archived=_boolean("include_archived") or False,
    )
    return jsonify(result), 200


@exercise_blueprint.post("/exercises")
@require_admin
def post_exercise() -> tuple[Response, int]:
    with transaction() as session:
        result = serialize_exercise(create_exercise(session, _write()))
    return jsonify(result), 201


@exercise_blueprint.get("/exercises/<exercise_id>")
def get_exercise(exercise_id: str) -> tuple[Response, int]:
    return jsonify(serialize_exercise(require_exercise(get_db(), exercise_id))), 200


@exercise_blueprint.patch("/exercises/<exercise_id>")
@require_admin
def patch_exercise(exercise_id: str) -> tuple[Response, int]:
    with transaction() as session:
        result = serialize_exercise(update_exercise(session, exercise_id, _write()))
    return jsonify(result), 200


@exercise_blueprint.delete("/exercises/<exercise_id>")
@require_admin
def delete_exercise(exercise_id: str) -> tuple[str, int]:
    with transaction() as session:
        archive_exercise(session, exercise_id)
    return "", 204
