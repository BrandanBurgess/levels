from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import cast
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from flask import Flask, current_app, g, request
from sqlalchemy import select

from levels_api.database import get_db
from levels_api.errors import ApiError
from levels_api.models import Profile, User, UserRole, UserStatus

from .rate_limit import LoginRateLimiter

AUTH_RATE_LIMITER_KEY = "levels_auth_rate_limiter"
PASSWORD_HASHER_KEY = "levels_password_hasher"


@dataclass(frozen=True, slots=True)
class Actor:
    user_id: str
    email: str
    role: UserRole
    is_demo: bool


def init_auth(app: Flask) -> None:
    app.extensions[AUTH_RATE_LIMITER_KEY] = LoginRateLimiter()
    app.extensions[PASSWORD_HASHER_KEY] = PasswordHasher()


def _configured_value(name: str) -> str:
    value = current_app.config.get(name)
    if not isinstance(value, str) or not value:
        raise ApiError(503, "AUTH_NOT_CONFIGURED", "Authentication is unavailable.")
    return value


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def hash_password(password: str) -> str:
    hasher = cast(PasswordHasher, current_app.extensions[PASSWORD_HASHER_KEY])
    return hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    hasher = cast(PasswordHasher, current_app.extensions[PASSWORD_HASHER_KEY])
    try:
        return hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def find_login_user(email: str, password: str) -> User | None:
    user = get_db().scalar(select(User).where(User.email_normalized == normalize_email(email)))
    if user is None or user.status is not UserStatus.ACTIVE or user.is_demo:
        return None
    return user if verify_password(user.password_hash, password) else None


def create_access_token(user: User) -> tuple[str, int]:
    secret = _configured_value("JWT_SECRET_KEY")
    expires_in = int(current_app.config["JWT_EXPIRES_SECONDS"])
    now = datetime.now(UTC)
    claims = {
        "sub": user.id,
        "role": user.role.value,
        "ver": user.token_version,
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


def authenticated_user() -> User:
    cached = g.get("authenticated_user")
    if isinstance(cached, User):
        return cached
    token = _bearer_token()
    if token is None:
        raise ApiError(401, "UNAUTHORIZED", "Authentication is required.")
    try:
        claims = jwt.decode(
            token,
            _configured_value("JWT_SECRET_KEY"),
            algorithms=["HS256"],
            issuer="levels-api",
            options={"require": ["sub", "role", "ver", "iss", "iat", "exp", "jti"]},
        )
    except jwt.PyJWTError as error:
        raise ApiError(401, "UNAUTHORIZED", "The access token is invalid or expired.") from error

    user_id = claims.get("sub")
    token_version = claims.get("ver")
    if not isinstance(user_id, str) or not isinstance(token_version, int):
        raise ApiError(401, "UNAUTHORIZED", "The access token is invalid or expired.")
    user = get_db().get(User, user_id)
    if (
        user is None
        or user.status is not UserStatus.ACTIVE
        or user.token_version != token_version
        or claims.get("role") != user.role.value
        or user.is_demo
    ):
        raise ApiError(401, "UNAUTHORIZED", "The access token is invalid or expired.")
    g.authenticated_user = user
    g.actor = Actor(user.id, user.email_normalized, user.role, user.is_demo)
    return user


def current_actor() -> Actor:
    user = authenticated_user()
    return Actor(user.id, user.email_normalized, user.role, user.is_demo)


def current_user_id() -> str:
    return authenticated_user().id


def optional_user() -> User | None:
    if _bearer_token() is None:
        return None
    return authenticated_user()


def require_user[**P, R](function: Callable[P, R]) -> Callable[P, R]:
    @wraps(function)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        authenticated_user()
        return function(*args, **kwargs)

    return wrapped


def current_user_payload(user: User) -> dict[str, str]:
    profile = get_db().scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is None:
        raise ApiError(500, "ACCOUNT_INCOMPLETE", "The account profile is unavailable.")
    return {
        "id": user.id,
        "email": user.email_normalized,
        "display_name": profile.display_name,
        "role": user.role.value,
        "account_status": user.status.value,
        "timezone": profile.timezone,
        "preferred_units": profile.preferred_units.value,
    }


# Compatibility names for feature modules while their tenant-scoping tickets land.
authenticated_admin = current_user_id
require_admin = require_user


def optional_admin() -> str | None:
    user = optional_user()
    return user.id if user is not None else None


def login_rate_limiter() -> LoginRateLimiter:
    return cast(LoginRateLimiter, current_app.extensions[AUTH_RATE_LIMITER_KEY])


def client_ip() -> str:
    return request.remote_addr or "unknown"
