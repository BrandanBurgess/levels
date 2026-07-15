from __future__ import annotations

from typing import cast

from flask import Flask, Response, request

ALLOWED_HEADERS = "Authorization, Content-Type, Idempotency-Key, X-Request-ID"
ALLOWED_METHODS = "GET, POST, PUT, PATCH, DELETE, OPTIONS"


def init_cors(app: Flask) -> None:
    @app.after_request
    def apply_cors_headers(response: Response) -> Response:
        origin = request.headers.get("Origin")
        allowed_origins = cast(tuple[str, ...], app.config["CORS_ALLOWED_ORIGINS"])
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Headers"] = ALLOWED_HEADERS
            response.headers["Access-Control-Allow-Methods"] = ALLOWED_METHODS
            response.headers.add("Vary", "Origin")
        return response
