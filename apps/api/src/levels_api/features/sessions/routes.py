from __future__ import annotations

from datetime import date
from typing import Any

from flask import Blueprint, Response, jsonify, request
from pydantic import BaseModel, ValidationError

from levels_api.auth import current_user_id, require_user
from levels_api.database import get_db, transaction
from levels_api.errors import ApiError

from .schemas import (
    AddSessionExercise,
    ReorderSessionExercises,
    SessionExerciseUpdate,
    SessionUpdate,
    SetWrite,
    StartSession,
)
from .service import (
    add_or_substitute_exercise,
    complete_session,
    create_set,
    delete_session,
    delete_set,
    exercise_payload,
    list_session_payloads,
    remove_session_exercise,
    reorder_session_exercises,
    require_session,
    session_payload,
    set_write_payload,
    start_session,
    update_session,
    update_session_exercise,
    update_set,
)

session_blueprint = Blueprint("sessions", __name__, url_prefix="/api/v1")


def _parse[RequestModel: BaseModel](model: type[RequestModel]) -> RequestModel:
    payload: Any = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError(422, "VALIDATION_ERROR", "A JSON request body is required.")
    try:
        return model.model_validate(payload)
    except ValidationError as error:
        fields = {
            ".".join(str(part) for part in item["loc"]): str(item["msg"]) for item in error.errors()
        }
        raise ApiError(
            422, "VALIDATION_ERROR", "One or more fields are invalid.", fields
        ) from error


def _date(name: str) -> date | None:
    value = request.args.get(name)
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ApiError(422, "VALIDATION_ERROR", f"{name} must be an ISO date.") from error


def _idempotency_key(*, required: bool = False) -> str | None:
    key = request.headers.get("Idempotency-Key")
    if key is None:
        if required:
            raise ApiError(422, "VALIDATION_ERROR", "Idempotency-Key is required.")
        return None
    if not 8 <= len(key) <= 128:
        raise ApiError(422, "VALIDATION_ERROR", "Idempotency-Key must be 8 to 128 characters.")
    return key


def _expected_version() -> int:
    raw = request.args.get("expected_version")
    try:
        value = int(raw) if raw is not None else -1
    except ValueError as error:
        raise ApiError(422, "VALIDATION_ERROR", "expected_version must be an integer.") from error
    if value < 0:
        raise ApiError(422, "VALIDATION_ERROR", "expected_version is required.")
    return value


def _boolean(name: str, default: bool = False) -> bool:
    value = request.args.get(name)
    if value is None:
        return default
    if value.casefold() in {"true", "1"}:
        return True
    if value.casefold() in {"false", "0"}:
        return False
    raise ApiError(422, "VALIDATION_ERROR", f"{name} must be true or false.")


@session_blueprint.get("/sessions")
@require_user
def get_sessions() -> tuple[Response, int]:
    result = list_session_payloads(
        get_db(),
        current_user_id(),
        date_from=_date("from"),
        date_to=_date("to"),
        exercise_id=request.args.get("exercise_id"),
    )
    return jsonify(result), 200


@session_blueprint.post("/sessions")
@require_user
def post_session() -> tuple[Response, int]:
    user_id = current_user_id()
    key = _idempotency_key(required=True)
    assert key is not None
    with transaction() as session:
        workout = start_session(session, user_id, _parse(StartSession), key)
        result = session_payload(workout)
    return jsonify(result), 201


@session_blueprint.get("/sessions/<session_id>")
@require_user
def get_session(session_id: str) -> tuple[Response, int]:
    session = get_db()
    workout = require_session(session, current_user_id(), session_id)
    return jsonify(session_payload(workout)), 200


@session_blueprint.patch("/sessions/<session_id>")
@require_user
def patch_session(session_id: str) -> tuple[Response, int]:
    user_id = current_user_id()
    with transaction() as session:
        workout = update_session(session, user_id, session_id, _parse(SessionUpdate))
        result = session_payload(workout)
    return jsonify(result), 200


@session_blueprint.delete("/sessions/<session_id>")
@require_user
def remove_session(session_id: str) -> tuple[str, int]:
    with transaction() as session:
        delete_session(session, current_user_id(), session_id)
    return "", 204


@session_blueprint.post("/sessions/<session_id>/exercises")
@require_user
def post_session_exercise(session_id: str) -> tuple[Response, int]:
    with transaction() as session:
        item = add_or_substitute_exercise(
            session, current_user_id(), session_id, _parse(AddSessionExercise)
        )
        result = exercise_payload(item)
    return jsonify(result), 201


@session_blueprint.patch("/sessions/<session_id>/exercises/<session_exercise_id>")
@require_user
def patch_session_exercise(session_id: str, session_exercise_id: str) -> tuple[Response, int]:
    with transaction() as session:
        workout = update_session_exercise(
            session,
            current_user_id(),
            session_id,
            session_exercise_id,
            _parse(SessionExerciseUpdate),
        )
        result = session_payload(workout)
    return jsonify(result), 200


@session_blueprint.delete("/sessions/<session_id>/exercises/<session_exercise_id>")
@require_user
def delete_session_exercise(session_id: str, session_exercise_id: str) -> tuple[Response, int]:
    with transaction() as session:
        workout = remove_session_exercise(
            session,
            current_user_id(),
            session_id,
            session_exercise_id,
            _expected_version(),
            confirm_logged_sets=_boolean("confirm_logged_sets"),
        )
        result = session_payload(workout)
    return jsonify(result), 200


@session_blueprint.post("/sessions/<session_id>/exercises/reorder")
@require_user
def post_session_exercise_reorder(session_id: str) -> tuple[Response, int]:
    with transaction() as session:
        workout = reorder_session_exercises(
            session,
            current_user_id(),
            session_id,
            _parse(ReorderSessionExercises),
        )
        result = session_payload(workout)
    return jsonify(result), 200


@session_blueprint.post("/sessions/<session_id>/sets")
@require_user
def post_set(session_id: str) -> tuple[Response, int]:
    with transaction() as session:
        set_log, records = create_set(
            session,
            current_user_id(),
            session_id,
            _parse(SetWrite),
            _idempotency_key(),
        )
        result = set_write_payload(set_log, records)
    return jsonify(result), 201


@session_blueprint.patch("/sets/<set_id>")
@require_user
def patch_set(set_id: str) -> tuple[Response, int]:
    with transaction() as session:
        set_log, records = update_set(session, current_user_id(), set_id, _parse(SetWrite))
        result = set_write_payload(set_log, records)
    return jsonify(result), 200


@session_blueprint.delete("/sets/<set_id>")
@require_user
def remove_set(set_id: str) -> tuple[str, int]:
    with transaction() as session:
        delete_set(session, current_user_id(), set_id)
    return "", 204


@session_blueprint.post("/sessions/<session_id>/complete")
@require_user
def post_complete_session(session_id: str) -> tuple[Response, int]:
    key = _idempotency_key(required=True)
    assert key is not None
    with transaction() as session:
        workout = complete_session(session, current_user_id(), session_id, key)
        result = session_payload(workout)
    return jsonify(result), 200
