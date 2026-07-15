from __future__ import annotations

from datetime import date

from flask import Blueprint, Response, jsonify, request

from levels_api.auth import current_user_id, require_user
from levels_api.database import get_db
from levels_api.errors import ApiError
from levels_api.features.profile.service import require_profile
from levels_api.features.water.service import local_date_for_profile

from .service import growth_suggestions

growth_blueprint = Blueprint("growth", __name__, url_prefix="/api/v1")


def _local_date() -> date:
    value = request.args.get("date")
    if value is None:
        return local_date_for_profile(require_profile(get_db(), current_user_id()).timezone)
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ApiError(400, "VALIDATION_ERROR", "date must be an ISO calendar date.") from error


@growth_blueprint.get("/growth/suggestions")
@require_user
def get_growth_suggestions() -> tuple[Response, int]:
    session = get_db()
    result = growth_suggestions(
        session,
        current_user_id(),
        _local_date(),
        split_day_id=request.args.get("split_day_id"),
    )
    return jsonify(result), 200
