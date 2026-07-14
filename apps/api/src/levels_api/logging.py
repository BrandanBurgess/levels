from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from flask import Flask, Response, g, has_request_context, request


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        request_id = getattr(record, "request_id", None)
        if request_id is None and has_request_context():
            request_id = getattr(g, "request_id", None)
        if request_id is not None:
            payload["request_id"] = request_id
        for key in ("method", "path", "status"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def configure_logging(app: Flask) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(str(app.config["LOG_LEVEL"]))
    app.logger.propagate = False


def _request_id() -> str:
    candidate = request.headers.get("X-Request-ID")
    if candidate is not None:
        try:
            return str(UUID(candidate))
        except ValueError:
            pass
    return str(uuid4())


def init_request_context(app: Flask) -> None:
    @app.before_request
    def assign_request_id() -> None:
        g.request_id = _request_id()

    @app.after_request
    def add_request_context(response: Response) -> Response:
        response.headers["X-Request-ID"] = g.request_id
        app.logger.info(
            "request.complete",
            extra={
                "request_id": g.request_id,
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
            },
        )
        return response
