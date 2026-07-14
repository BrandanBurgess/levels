from __future__ import annotations

from flask import Flask


def create_app() -> Flask:
    """Create the LEVELS Flask application."""
    app = Flask(__name__)
    app.config.from_prefixed_env(prefix="LEVELS")

    @app.get("/")
    def index() -> dict[str, str]:
        return {"name": "LEVELS API", "status": "bootstrapped"}

    return app


__all__ = ["create_app"]
