from __future__ import annotations

from datetime import date

from flask import Blueprint, Response, jsonify, request

from levels_api.auth import optional_admin
from levels_api.database import get_db
from levels_api.errors import ApiError
from levels_api.features.profile.service import require_profile
from levels_api.features.water.service import local_date_for_profile

from .service import dashboard

today_blueprint = Blueprint("today", __name__, url_prefix="/api/v1/public")


def _dashboard_date() -> date:
    value = request.args.get("date")
    if value is None:
        return local_date_for_profile(require_profile(get_db()).timezone)
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ApiError(
            400,
            "VALIDATION_ERROR",
            "One or more fields are invalid.",
            {"date": "Must be an ISO calendar date."},
        ) from error


@today_blueprint.get("/dashboard")
def public_dashboard() -> tuple[Response, int]:
    owner = optional_admin() is not None
    return jsonify(dashboard(get_db(), _dashboard_date(), owner=owner)), 200
