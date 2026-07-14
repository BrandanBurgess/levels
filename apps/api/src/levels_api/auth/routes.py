from __future__ import annotations

from typing import Any, cast

from flask import Blueprint, Response, jsonify, request
from sqlalchemy import select

from levels_api.database import get_db
from levels_api.errors import ApiError
from levels_api.models import Profile

from .service import client_ip, create_access_token, login_rate_limiter, verify_credentials

auth_blueprint = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


def _login_payload() -> tuple[str, str]:
    payload: Any = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError(400, "VALIDATION_ERROR", "A JSON request body is required.")
    unexpected = set(payload) - {"username", "password"}
    username = payload.get("username")
    password = payload.get("password")
    field_errors: dict[str, str] = {}
    if unexpected:
        field_errors["body"] = "Unexpected fields are not allowed."
    if not isinstance(username, str) or not 1 <= len(username) <= 100:
        field_errors["username"] = "Must contain between 1 and 100 characters."
    if not isinstance(password, str) or not 1 <= len(password) <= 500:
        field_errors["password"] = "Must contain between 1 and 500 characters."
    if field_errors:
        raise ApiError(400, "VALIDATION_ERROR", "One or more fields are invalid.", field_errors)
    return cast(str, username), cast(str, password)


@auth_blueprint.post("/login")
def login() -> tuple[Response, int]:
    username, password = _login_payload()
    ip_address = client_ip()
    limiter = login_rate_limiter()
    if limiter.blocked(ip_address, username):
        raise ApiError(429, "RATE_LIMITED", "Too many login attempts. Try again later.")
    if not verify_credentials(username, password):
        limiter.record_failure(ip_address, username)
        raise ApiError(401, "INVALID_CREDENTIALS", "Invalid username or password.")

    limiter.clear(ip_address, username)
    access_token, expires_in = create_access_token(username)
    display_name = get_db().scalar(select(Profile.display_name).limit(1)) or username
    return (
        jsonify(
            {
                "access_token": access_token,
                "expires_in_seconds": expires_in,
                "admin": {"display_name": display_name},
            }
        ),
        200,
    )
