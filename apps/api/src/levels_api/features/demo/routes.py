from __future__ import annotations

from flask import Blueprint, Response, jsonify

from levels_api.database import get_db

from .service import demo_bootstrap

demo_blueprint = Blueprint("demo", __name__, url_prefix="/api/v1/demo")


@demo_blueprint.get("/bootstrap")
def bootstrap() -> Response:
    return jsonify(demo_bootstrap(get_db()))
