from __future__ import annotations

from flask import Blueprint, Response, jsonify

from levels_api.auth import current_user_id, require_user
from levels_api.database import get_db

from .service import streak_summary

streak_blueprint = Blueprint("streak", __name__, url_prefix="/api/v1/me/streak")


@streak_blueprint.get("")
@require_user
def read_streak() -> Response:
    return jsonify(streak_summary(get_db(), current_user_id()))
