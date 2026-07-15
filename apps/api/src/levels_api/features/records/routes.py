from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from levels_api.auth import current_user_id, require_user
from levels_api.database import get_db
from levels_api.errors import ApiError

from .service import list_record_payloads

record_blueprint = Blueprint("records", __name__, url_prefix="/api/v1")


def _current_only() -> bool:
    value = request.args.get("current_only", "true").lower()
    if value in {"true", "1"}:
        return True
    if value in {"false", "0"}:
        return False
    raise ApiError(400, "VALIDATION_ERROR", "current_only must be true or false.")


@record_blueprint.get("/records")
@require_user
def get_records() -> tuple[Response, int]:
    result = list_record_payloads(
        get_db(),
        current_user_id(),
        exercise_id=request.args.get("exercise_id"),
        current_only=_current_only(),
    )
    return jsonify(result), 200
