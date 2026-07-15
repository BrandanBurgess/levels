from __future__ import annotations

from datetime import UTC, datetime

from flask import Blueprint, Response, current_app, jsonify, request

from levels_api.auth import current_user_id, require_user
from levels_api.database import get_db
from levels_api.errors import ApiError

from .service import export_csv, export_payload

export_blueprint = Blueprint("export", __name__, url_prefix="/api/v1")


@export_blueprint.get("/export")
@require_user
def get_export() -> Response | tuple[Response, int]:
    export_format = request.args.get("format")
    if export_format not in {"json", "csv"}:
        raise ApiError(400, "VALIDATION_ERROR", "format must be json or csv.")
    payload = export_payload(
        get_db(),
        current_user_id(),
        exported_at=datetime.now(UTC),
        version=str(current_app.config["API_VERSION"]),
    )
    stamp = datetime.now(UTC).date().isoformat()
    if export_format == "json":
        response = jsonify(payload)
        response.headers["Content-Disposition"] = (
            f'attachment; filename="levels-export-{stamp}.json"'
        )
        return response, 200
    return Response(
        export_csv(payload),
        status=200,
        content_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="levels-export-{stamp}.csv"'},
    )
