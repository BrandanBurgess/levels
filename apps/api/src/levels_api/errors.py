from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from flask import Flask, current_app, g, jsonify
from werkzeug.exceptions import HTTPException


@dataclass(slots=True)
class ApiError(Exception):
    status_code: int
    code: str
    message: str
    field_errors: dict[str, str] = field(default_factory=dict)


def error_response(error: ApiError) -> tuple[Any, int]:
    details: dict[str, Any] = {
        "code": error.code,
        "message": error.message,
        "request_id": g.request_id,
    }
    if error.field_errors:
        details["field_errors"] = error.field_errors
    return jsonify({"error": details}), error.status_code


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError) -> tuple[Any, int]:
        return error_response(error)

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException) -> tuple[Any, int]:
        code = error.name.upper().replace(" ", "_")
        message = error.description or "The request could not be completed."
        return error_response(ApiError(error.code or 500, code, message))

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception) -> tuple[Any, int]:
        current_app.logger.exception("Unhandled application error", exc_info=error)
        return error_response(
            ApiError(500, "INTERNAL_SERVER_ERROR", "An unexpected error occurred.")
        )
