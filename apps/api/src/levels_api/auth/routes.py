from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import Blueprint, Response, current_app, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from levels_api.database import get_db, transaction
from levels_api.errors import ApiError
from levels_api.models import PreferredUnits, User, UserRole, UserStatus
from levels_api.seed.loader import seed_user_starter

from .service import (
    authenticated_user,
    client_ip,
    create_access_token,
    current_user_payload,
    find_login_user,
    hash_password,
    login_rate_limiter,
    normalize_email,
    require_user,
)

auth_blueprint = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


def _json_object(allowed_fields: set[str]) -> dict[str, Any]:
    payload: Any = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError(422, "VALIDATION_ERROR", "A JSON request body is required.")
    unexpected = set(payload) - allowed_fields
    if unexpected:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "One or more fields are invalid.",
            {"body": "Unexpected fields are not allowed."},
        )
    return cast(dict[str, Any], payload)


def _valid_email(value: object) -> bool:
    if not isinstance(value, str) or not 3 <= len(value) <= 254:
        return False
    local, separator, domain = value.strip().rpartition("@")
    return bool(separator and local and "." in domain and not domain.startswith("."))


def _login_payload() -> tuple[str, str]:
    payload = _json_object({"email", "password"})
    email = payload.get("email")
    password = payload.get("password")
    field_errors: dict[str, str] = {}
    if not _valid_email(email):
        field_errors["email"] = "Must be a valid email address."
    if not isinstance(password, str) or not 1 <= len(password) <= 256:
        field_errors["password"] = "Must contain between 1 and 256 characters."
    if field_errors:
        raise ApiError(422, "VALIDATION_ERROR", "One or more fields are invalid.", field_errors)
    return cast(str, email), cast(str, password)


def _registration_payload() -> tuple[str, str, str, str, PreferredUnits]:
    payload = _json_object({"email", "password", "display_name", "timezone", "preferred_units"})
    email = payload.get("email")
    password = payload.get("password")
    display_name = payload.get("display_name")
    timezone = payload.get("timezone", "America/Toronto")
    preferred_units = payload.get("preferred_units", "metric")
    field_errors: dict[str, str] = {}
    if not _valid_email(email):
        field_errors["email"] = "Must be a valid email address."
    if not isinstance(password, str) or not 10 <= len(password) <= 256:
        field_errors["password"] = "Must contain between 10 and 256 characters."
    if not isinstance(display_name, str) or not 1 <= len(display_name.strip()) <= 80:
        field_errors["display_name"] = "Must contain between 1 and 80 characters."
    if not isinstance(timezone, str) or not timezone or len(timezone) > 100:
        field_errors["timezone"] = "Must be a valid IANA timezone."
    else:
        try:
            ZoneInfo(timezone)
        except ZoneInfoNotFoundError:
            field_errors["timezone"] = "Must be a valid IANA timezone."
    try:
        units = PreferredUnits(preferred_units)
    except (TypeError, ValueError):
        field_errors["preferred_units"] = "Must be metric or imperial."
        units = PreferredUnits.METRIC
    if field_errors:
        raise ApiError(422, "VALIDATION_ERROR", "One or more fields are invalid.", field_errors)
    return (
        normalize_email(cast(str, email)),
        cast(str, password),
        cast(str, display_name).strip(),
        cast(str, timezone),
        units,
    )


def _auth_response(user: User) -> tuple[Response, int]:
    access_token, expires_in = create_access_token(user)
    return (
        jsonify(
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": expires_in,
                "user": current_user_payload(user),
            }
        ),
        200,
    )


@auth_blueprint.post("/login")
def login() -> tuple[Response, int]:
    email, password = _login_payload()
    normalized_email = normalize_email(email)
    ip_address = client_ip()
    limiter = login_rate_limiter()
    if limiter.blocked(ip_address, normalized_email):
        raise ApiError(429, "RATE_LIMITED", "Too many login attempts. Try again later.")
    user = find_login_user(normalized_email, password)
    if user is None:
        limiter.record_failure(ip_address, normalized_email)
        raise ApiError(401, "INVALID_CREDENTIALS", "Invalid email or password.")

    limiter.clear(ip_address, normalized_email)
    user.last_login_at = datetime.now(UTC)
    get_db().commit()
    return _auth_response(user)


@auth_blueprint.post("/register")
def register() -> tuple[Response, int]:
    if not bool(current_app.config["REGISTRATION_ENABLED"]):
        raise ApiError(403, "REGISTRATION_DISABLED", "Account registration is disabled.")
    email, password, display_name, timezone, preferred_units = _registration_payload()
    ip_address = client_ip()
    limiter = login_rate_limiter()
    if limiter.blocked(ip_address, email):
        raise ApiError(429, "RATE_LIMITED", "Too many registration attempts. Try again later.")

    try:
        with transaction() as session:
            if session.scalar(select(User.id).where(User.email_normalized == email)) is not None:
                raise ApiError(409, "ACCOUNT_EXISTS", "An account already exists for this email.")
            user = User(
                email_normalized=email,
                password_hash=hash_password(password),
                status=UserStatus.ACTIVE,
                role=UserRole.MEMBER,
                token_version=0,
                is_demo=False,
            )
            session.add(user)
            session.flush()
            seed_user_starter(
                session,
                user,
                display_name=display_name,
                timezone=timezone,
                preferred_units=preferred_units,
            )
    except IntegrityError as error:
        raise ApiError(
            409, "ACCOUNT_EXISTS", "An account already exists for this email."
        ) from error

    response, _ = _auth_response(user)
    return response, 201


@auth_blueprint.get("/me")
@require_user
def me() -> Response:
    return jsonify(current_user_payload(authenticated_user()))


@auth_blueprint.post("/logout")
@require_user
def logout() -> tuple[str, int]:
    user = authenticated_user()
    user.token_version += 1
    get_db().commit()
    return "", 204
