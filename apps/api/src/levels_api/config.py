from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

DEFAULT_DATABASE_URL = "sqlite+pysqlite:///./levels-dev.db"
DEFAULT_ORIGIN = "http://localhost:5173"
VALID_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
TEST_JWT_SECRET = "levels-test-jwt-secret-at-least-32-characters"


class ConfigurationError(ValueError):
    """Raised when application environment values are unsafe or incomplete."""


def _parse_origins(raw: str) -> tuple[str, ...]:
    origins = tuple(
        dict.fromkeys(part.strip().rstrip("/") for part in raw.split(",") if part.strip())
    )
    if not origins:
        raise ConfigurationError("CORS_ALLOWED_ORIGINS must contain at least one origin")
    for origin in origins:
        parsed = urlsplit(origin)
        if origin == "*" or parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ConfigurationError(f"Invalid CORS origin: {origin!r}")
        if parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ConfigurationError(f"CORS entries must be exact origins: {origin!r}")
    return origins


def _parse_bool(name: str, raw: str) -> bool:
    value = raw.strip().casefold()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} must be true or false")


@dataclass(frozen=True, slots=True)
class Settings:
    app_env: str
    app_timezone: str
    database_url: str
    turso_auth_token: str | None
    cors_allowed_origins: tuple[str, ...]
    public_web_origin: str
    log_level: str
    registration_enabled: bool = True
    bootstrap_owner_email: str | None = None
    bootstrap_owner_password_hash: str | None = None
    # Retained only so stacked v1 tests can be migrated incrementally; runtime auth ignores them.
    admin_username: str | None = None
    admin_password_hash: str | None = None
    jwt_secret_key: str | None = None
    jwt_expires_seconds: int = 900
    testing: bool = False

    @classmethod
    def from_environment(cls) -> Settings:
        return cls.from_mapping(os.environ)

    @classmethod
    def from_mapping(cls, values: Mapping[str, str]) -> Settings:
        app_env = values.get("APP_ENV", "development").strip().lower()
        database_url = values.get("DATABASE_URL", DEFAULT_DATABASE_URL).strip()
        turso_auth_token = values.get("TURSO_AUTH_TOKEN", "").strip() or None
        log_level = values.get("LOG_LEVEL", "INFO").strip().upper()
        public_web_origin = values.get("PUBLIC_WEB_ORIGIN", DEFAULT_ORIGIN).strip().rstrip("/")
        origins = _parse_origins(values.get("CORS_ALLOWED_ORIGINS", DEFAULT_ORIGIN))
        admin_username = values.get("ADMIN_USERNAME", "").strip() or None
        admin_password_hash = values.get("ADMIN_PASSWORD_HASH", "").strip() or None
        jwt_secret_key = values.get("JWT_SECRET_KEY", "").strip() or None
        registration_enabled = _parse_bool(
            "REGISTRATION_ENABLED", values.get("REGISTRATION_ENABLED", "true")
        )
        bootstrap_owner_email = values.get("BOOTSTRAP_OWNER_EMAIL", "").strip().casefold() or None
        bootstrap_owner_password_hash = (
            values.get("BOOTSTRAP_OWNER_PASSWORD_HASH", "").strip() or None
        )

        if app_env not in {"development", "test", "production"}:
            raise ConfigurationError("APP_ENV must be development, test, or production")
        if not database_url:
            raise ConfigurationError("DATABASE_URL is required")
        if database_url.startswith("libsql://") and turso_auth_token is None:
            raise ConfigurationError("TURSO_AUTH_TOKEN is required for a libsql DATABASE_URL")
        if log_level not in VALID_LOG_LEVELS:
            raise ConfigurationError(f"Invalid LOG_LEVEL: {log_level!r}")
        if public_web_origin not in origins:
            raise ConfigurationError("PUBLIC_WEB_ORIGIN must be present in CORS_ALLOWED_ORIGINS")
        if admin_password_hash is not None and not admin_password_hash.startswith("$argon2"):
            raise ConfigurationError("ADMIN_PASSWORD_HASH must be an Argon2 hash")
        if (
            bootstrap_owner_password_hash is not None
            and not bootstrap_owner_password_hash.startswith("$argon2")
        ):
            raise ConfigurationError("BOOTSTRAP_OWNER_PASSWORD_HASH must be an Argon2 hash")
        if (bootstrap_owner_email is None) != (bootstrap_owner_password_hash is None):
            raise ConfigurationError(
                "BOOTSTRAP_OWNER_EMAIL and BOOTSTRAP_OWNER_PASSWORD_HASH must be set together"
            )
        if app_env == "production":
            if jwt_secret_key is None:
                raise ConfigurationError("JWT_SECRET_KEY is required in production")
            if len(jwt_secret_key or "") < 32:
                raise ConfigurationError("JWT_SECRET_KEY must contain at least 32 characters")

        return cls(
            app_env=app_env,
            app_timezone=values.get("APP_TIMEZONE", "America/Toronto").strip(),
            database_url=database_url,
            turso_auth_token=turso_auth_token,
            cors_allowed_origins=origins,
            public_web_origin=public_web_origin,
            log_level=log_level,
            registration_enabled=registration_enabled,
            bootstrap_owner_email=bootstrap_owner_email,
            bootstrap_owner_password_hash=bootstrap_owner_password_hash,
            admin_username=admin_username,
            admin_password_hash=admin_password_hash,
            jwt_secret_key=jwt_secret_key,
            testing=app_env == "test",
        )

    @classmethod
    def for_testing(
        cls,
        database_url: str = "sqlite+pysqlite:///:memory:",
        *,
        cors_allowed_origins: tuple[str, ...] = (DEFAULT_ORIGIN,),
        admin_username: str | None = None,
        admin_password_hash: str | None = None,
        jwt_secret_key: str | None = None,
        registration_enabled: bool = True,
    ) -> Settings:
        return cls(
            app_env="test",
            app_timezone="America/Toronto",
            database_url=database_url,
            turso_auth_token=None,
            cors_allowed_origins=cors_allowed_origins,
            public_web_origin=cors_allowed_origins[0],
            log_level="ERROR",
            registration_enabled=registration_enabled,
            admin_username=admin_username,
            admin_password_hash=admin_password_hash,
            jwt_secret_key=jwt_secret_key or TEST_JWT_SECRET,
            testing=True,
        )
