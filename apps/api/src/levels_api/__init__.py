from __future__ import annotations

from flask import Flask

from .auth.routes import auth_blueprint
from .auth.service import init_auth
from .config import Settings
from .cors import init_cors
from .database import init_database
from .errors import register_error_handlers
from .features.exercises.routes import exercise_blueprint
from .features.profile.routes import profile_blueprint
from .features.sessions.routes import session_blueprint
from .features.splits.routes import split_blueprint
from .features.today.routes import today_blueprint
from .features.water.routes import water_blueprint
from .logging import configure_logging, init_request_context
from .routes.health import health_blueprint

__version__ = "0.1.0"


def create_app(settings: Settings | None = None) -> Flask:
    """Create and configure the LEVELS Flask application."""
    resolved_settings = settings or Settings.from_environment()
    app = Flask(__name__)
    app.config.update(
        APP_ENV=resolved_settings.app_env,
        APP_TIMEZONE=resolved_settings.app_timezone,
        DATABASE_URL=resolved_settings.database_url,
        TURSO_AUTH_TOKEN=resolved_settings.turso_auth_token,
        CORS_ALLOWED_ORIGINS=resolved_settings.cors_allowed_origins,
        PUBLIC_WEB_ORIGIN=resolved_settings.public_web_origin,
        LOG_LEVEL=resolved_settings.log_level,
        ADMIN_USERNAME=resolved_settings.admin_username,
        ADMIN_PASSWORD_HASH=resolved_settings.admin_password_hash,
        JWT_SECRET_KEY=resolved_settings.jwt_secret_key,
        JWT_EXPIRES_SECONDS=resolved_settings.jwt_expires_seconds,
        API_VERSION=__version__,
        TESTING=resolved_settings.testing,
    )

    configure_logging(app)
    init_request_context(app)
    init_cors(app)
    init_database(app)
    init_auth(app)
    register_error_handlers(app)
    app.register_blueprint(health_blueprint)
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(exercise_blueprint)
    app.register_blueprint(profile_blueprint)
    app.register_blueprint(session_blueprint)
    app.register_blueprint(split_blueprint)
    app.register_blueprint(today_blueprint)
    app.register_blueprint(water_blueprint)
    return app


__all__ = ["Settings", "__version__", "create_app"]
