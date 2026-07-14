from __future__ import annotations

from datetime import date
from typing import Any

from flask import Blueprint, Response, jsonify, request
from pydantic import BaseModel, ValidationError

from levels_api.auth import optional_admin, require_admin
from levels_api.database import get_db, transaction
from levels_api.errors import ApiError

from .schemas import AddSessionExercise, SessionUpdate, SetWrite, StartSession
from .service import (
    add_or_substitute_exercise,
    complete_session,
    create_set,
    delete_session,
    delete_set,
    exercise_payload,
    list_session_payloads,
    require_session,
    session_payload,
    set_write_payload,
    start_session,
    update_session,
    update_set,
)

session_blueprint = Blueprint("sessions", __name__, url_prefix="/api/v1")


def _parse[RequestModel: BaseModel](model: type[RequestModel]) -> RequestModel:
    payload: Any = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError(400, "VALIDATION_ERROR", "A JSON request body is required.")
    try:
        return model.model_validate(payload)
    except ValidationError as error:
        fields = {
            ".".join(str(part) for part in item["loc"]): str(item["msg"]) for item in error.errors()
        }
        raise ApiError(
            400, "VALIDATION_ERROR", "One or more fields are invalid.", fields
        ) from error


def _date(name: str) -> date | None:
    value = request.args.get(name)
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ApiError(400, "VALIDATION_ERROR", f"{name} must be an ISO date.") from error


def _public_only() -> bool:
    value = request.args.get("public_only", "true").lower()
    if value in {"true", "1"}:
        return True
    if value in {"false", "0"}:
        return False
    raise ApiError(400, "VALIDATION_ERROR", "public_only must be true or false.")


@session_blueprint.get("/sessions")
def get_sessions() -> tuple[Response, int]:
    owner = optional_admin() is not None
    result = list_session_payloads(
        get_db(),
        owner=owner,
        public_only=_public_only(),
        date_from=_date("from"),
        date_to=_date("to"),
        exercise_id=request.args.get("exercise_id"),
    )
    return jsonify(result), 200


@session_blueprint.post("/sessions")
@require_admin
def post_session() -> tuple[Response, int]:
    key = request.headers.get("Idempotency-Key")
    if key is not None and not 8 <= len(key) <= 128:
        raise ApiError(400, "VALIDATION_ERROR", "Idempotency-Key must be 8 to 128 characters.")
    with transaction() as session:
        workout = start_session(session, _parse(StartSession), key)
        result = session_payload(session, workout, owner=True)
    return jsonify(result), 201


@session_blueprint.get("/sessions/<session_id>")
def get_session(session_id: str) -> tuple[Response, int]:
    session = get_db()
    owner = optional_admin() is not None
    return jsonify(session_payload(session, require_session(session, session_id), owner=owner)), 200


@session_blueprint.patch("/sessions/<session_id>")
@require_admin
def patch_session(session_id: str) -> tuple[Response, int]:
    with transaction() as session:
        workout = update_session(session, session_id, _parse(SessionUpdate))
        result = session_payload(session, workout, owner=True)
    return jsonify(result), 200


@session_blueprint.delete("/sessions/<session_id>")
@require_admin
def remove_session(session_id: str) -> tuple[str, int]:
    with transaction() as session:
        delete_session(session, session_id)
    return "", 204


def _idempotency_key() -> str | None:
    key = request.headers.get("Idempotency-Key")
    if key is not None and not 8 <= len(key) <= 128:
        raise ApiError(400, "VALIDATION_ERROR", "Idempotency-Key must be 8 to 128 characters.")
    return key


@session_blueprint.post("/sessions/<session_id>/exercises")
@require_admin
def post_session_exercise(session_id: str) -> tuple[Response, int]:
    with transaction() as session:
        item = add_or_substitute_exercise(session, session_id, _parse(AddSessionExercise))
        result = exercise_payload(item)
    return jsonify(result), 201


@session_blueprint.post("/sessions/<session_id>/sets")
@require_admin
def post_set(session_id: str) -> tuple[Response, int]:
    with transaction() as session:
        set_log, records = create_set(session, session_id, _parse(SetWrite), _idempotency_key())
        result = set_write_payload(set_log, records)
    return jsonify(result), 201


@session_blueprint.patch("/sets/<set_id>")
@require_admin
def patch_set(set_id: str) -> tuple[Response, int]:
    with transaction() as session:
        set_log, records = update_set(session, set_id, _parse(SetWrite))
        result = set_write_payload(set_log, records)
    return jsonify(result), 200


@session_blueprint.delete("/sets/<set_id>")
@require_admin
def remove_set(set_id: str) -> tuple[str, int]:
    with transaction() as session:
        delete_set(session, set_id)
    return "", 204


@session_blueprint.post("/sessions/<session_id>/complete")
@require_admin
def post_complete_session(session_id: str) -> tuple[Response, int]:
    with transaction() as session:
        workout = complete_session(session, session_id)
        result = session_payload(session, workout, owner=True)
    return jsonify(result), 200
