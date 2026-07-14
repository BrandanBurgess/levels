from __future__ import annotations

from flask import Blueprint, Response, current_app, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from levels_api.database import get_engine

health_blueprint = Blueprint("health", __name__)


def _health_payload() -> dict[str, str]:
    database_status = "ok"
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        current_app.logger.warning("health.database_degraded", exc_info=True)
        database_status = "degraded"
    return {
        "status": "ok",
        "version": str(current_app.config["API_VERSION"]),
        "database": database_status,
    }


@health_blueprint.get("/api/v1/health")
def api_health() -> tuple[Response, int]:
    return jsonify(_health_payload()), 200


@health_blueprint.get("/health")
def provider_health() -> tuple[Response, int]:
    return jsonify(_health_payload()), 200
