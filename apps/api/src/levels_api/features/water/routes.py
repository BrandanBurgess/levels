from __future__ import annotations

from datetime import date
from typing import Any

from flask import Blueprint, Response, jsonify, request
from pydantic import ValidationError

from levels_api.auth import optional_admin, require_admin
from levels_api.database import get_db, transaction
from levels_api.errors import ApiError
from levels_api.features.profile.service import require_profile

from .schemas import WaterWrite
from .service import add_water, local_date_for_profile, undo_latest, water_day

water_blueprint = Blueprint("water", __name__, url_prefix="/api/v1/water")


def _requested_date(timezone: str | None = None) -> date:
    value = request.args.get("date")
    if value is None:
        resolved_timezone = timezone or require_profile(get_db()).timezone
        return local_date_for_profile(resolved_timezone)
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ApiError(
            400,
            "VALIDATION_ERROR",
            "One or more fields are invalid.",
            {"date": "Must be an ISO calendar date."},
        ) from error


def _parse_write() -> WaterWrite:
    payload: Any = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError(400, "VALIDATION_ERROR", "A JSON request body is required.")
    try:
        return WaterWrite.model_validate(payload)
    except ValidationError as error:
        fields = {
            ".".join(str(part) for part in item["loc"]): str(item["msg"]) for item in error.errors()
        }
        raise ApiError(
            400, "VALIDATION_ERROR", "One or more fields are invalid.", fields
        ) from error


@water_blueprint.get("/today")
def get_today_water() -> tuple[Response, int]:
    owner = optional_admin()
    profile = require_profile(get_db())
    assert profile.visibility is not None
    if owner is None and not profile.visibility.show_water:
        raise ApiError(404, "NOT_FOUND", "The requested resource was not found.")
    return jsonify(water_day(get_db(), _requested_date())), 200


@water_blueprint.post("/today")
@require_admin
def post_water() -> tuple[Response, int]:
    write = _parse_write()
    with transaction() as session:
        result = add_water(session, write, request.headers.get("Idempotency-Key"))
    return jsonify(result), 201


@water_blueprint.post("/today/undo")
@require_admin
def post_undo_water() -> tuple[Response, int]:
    with transaction() as session:
        profile = require_profile(session)
        result = undo_latest(session, _requested_date(profile.timezone))
    return jsonify(result), 200
