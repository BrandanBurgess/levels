from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from flask import Blueprint, Response, jsonify, request
from pydantic import BaseModel, ValidationError

from levels_api.auth import current_user_id, require_user
from levels_api.database import get_db, transaction
from levels_api.errors import ApiError

from . import repository
from .schemas import SkipTodayRequest, TodayExercisePlanUpdate, TodayOverrideRequest
from .service import (
    delete_override,
    put_override,
    replace_exercise_plan,
    skip_today,
    today_payload,
)

today_blueprint = Blueprint("today", __name__, url_prefix="/api/v1")


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


def _iso_date(value: str | None, name: str) -> date:
    if value is None:
        raise ApiError(422, "VALIDATION_ERROR", f"{name} is required.")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ApiError(422, "VALIDATION_ERROR", f"{name} must be an ISO date.") from error


def _today_date(user_id: str) -> date:
    value = request.args.get("date")
    if value is not None:
        return _iso_date(value, "date")
    profile = repository.profile(get_db(), user_id)
    if profile is None:
        raise ApiError(503, "DATA_NOT_INITIALIZED", "Account data is unavailable.")
    return datetime.now(UTC).astimezone(ZoneInfo(profile.timezone)).date()


def _expected_version() -> int:
    raw = request.args.get("expected_version")
    if raw is None:
        raise ApiError(422, "VALIDATION_ERROR", "expected_version is required.")
    try:
        value = int(raw)
    except ValueError as error:
        raise ApiError(422, "VALIDATION_ERROR", "expected_version must be an integer.") from error
    if value < 0:
        raise ApiError(422, "VALIDATION_ERROR", "expected_version must be non-negative.")
    return value


def _idempotency_key() -> str:
    key = request.headers.get("Idempotency-Key")
    if key is None or not 8 <= len(key) <= 128:
        raise ApiError(422, "VALIDATION_ERROR", "Idempotency-Key must be 8 to 128 characters.")
    return key


@today_blueprint.get("/today")
@require_user
def get_today() -> tuple[Response, int]:
    user_id = current_user_id()
    return jsonify(today_payload(get_db(), user_id, _today_date(user_id))), 200


@today_blueprint.put("/today/override")
@require_user
def update_today_override() -> tuple[Response, int]:
    user_id = current_user_id()
    write = _parse(TodayOverrideRequest)
    with transaction() as session:
        put_override(session, user_id, write, _idempotency_key())
        result = today_payload(session, user_id, write.local_date)
    return jsonify(result), 200


@today_blueprint.delete("/today/override")
@require_user
def remove_today_override() -> tuple[str, int]:
    user_id = current_user_id()
    local_date = _iso_date(request.args.get("local_date"), "local_date")
    with transaction() as session:
        delete_override(session, user_id, local_date, _expected_version())
    return "", 204


@today_blueprint.post("/today/skip")
@require_user
def post_today_skip() -> tuple[Response, int]:
    user_id = current_user_id()
    write = _parse(SkipTodayRequest)
    with transaction() as session:
        skip_today(session, user_id, write, _idempotency_key())
        result = today_payload(session, user_id, write.local_date)
    return jsonify(result), 200


@today_blueprint.put("/today/exercises")
@require_user
def put_today_exercises() -> tuple[Response, int]:
    user_id = current_user_id()
    write = _parse(TodayExercisePlanUpdate)
    with transaction() as session:
        replace_exercise_plan(session, user_id, write, _idempotency_key())
        result = today_payload(session, user_id, write.local_date)
    return jsonify(result), 200
