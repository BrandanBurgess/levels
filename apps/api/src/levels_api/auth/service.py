from __future__ import annotations

import hmac
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import cast
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from flask import Flask, current_app, g, request

from levels_api.errors import ApiError

from .rate_limit import LoginRateLimiter

AUTH_RATE_LIMITER_KEY = "levels_auth_rate_limiter"
PASSWORD_HASHER_KEY = "levels_password_hasher"


def init_auth(app: Flask) -> None:
    app.extensions[AUTH_RATE_LIMITER_KEY] = LoginRateLimiter()
    app.extensions[PASSWORD_HASHER_KEY] = PasswordHasher()


def _configured_value(name: str) -> str:
    value = current_app.config.get(name)
    if not isinstance(value, str) or not value:
        raise ApiError(503, "AUTH_NOT_CONFIGURED", "Owner authentication is unavailable.")
    return value


def verify_credentials(username: str, password: str) -> bool:
    configured_username = _configured_value("ADMIN_USERNAME")
    configured_hash = _configured_value("ADMIN_PASSWORD_HASH")
    hasher = cast(PasswordHasher, current_app.extensions[PASSWORD_HASHER_KEY])
    password_valid = False
    try:
        password_valid = hasher.verify(configured_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        password_valid = False
    username_valid = hmac.compare_digest(username.casefold(), configured_username.casefold())
    return username_valid and password_valid


def create_access_token(username: str) -> tuple[str, int]:
    secret = _configured_value("JWT_SECRET_KEY")
    expires_in = int(current_app.config["JWT_EXPIRES_SECONDS"])
    now = datetime.now(UTC)
    claims = {
        "sub": username,
        "role": "owner",
        "iss": "levels-api",
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "jti": str(uuid4()),
    }
    return jwt.encode(claims, secret, algorithm="HS256"), expires_in


def _bearer_token() -> str | None:
    header = request.headers.get("Authorization", "")
    scheme, separator, token = header.partition(" ")
    if separator and scheme.casefold() == "bearer" and token and " " not in token:
        return token
    return None


def authenticated_admin() -> str:
    token = _bearer_token()
    if token is None:
        raise ApiError(401, "UNAUTHORIZED", "Authentication is required.")
    try:
        claims = jwt.decode(
            token,
            _configured_value("JWT_SECRET_KEY"),
            algorithms=["HS256"],
            issuer="levels-api",
            options={"require": ["sub", "role", "iss", "iat", "exp", "jti"]},
        )
    except jwt.PyJWTError as error:
        raise ApiError(401, "UNAUTHORIZED", "The access token is invalid or expired.") from error
    username = claims.get("sub")
    configured_username = _configured_value("ADMIN_USERNAME")
    if (
        not isinstance(username, str)
        or claims.get("role") != "owner"
        or not hmac.compare_digest(username.casefold(), configured_username.casefold())
    ):
        raise ApiError(401, "UNAUTHORIZED", "The access token is invalid or expired.")
    g.admin_username = username
    return username


def optional_admin() -> str | None:
    if _bearer_token() is None:
        return None
    return authenticated_admin()


def require_admin[**P, R](function: Callable[P, R]) -> Callable[P, R]:
    @wraps(function)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        authenticated_admin()
        return function(*args, **kwargs)

    return wrapped


def login_rate_limiter() -> LoginRateLimiter:
    return cast(LoginRateLimiter, current_app.extensions[AUTH_RATE_LIMITER_KEY])


def client_ip() -> str:
    return request.remote_addr or "unknown"
