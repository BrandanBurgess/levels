from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import cast

from flask import Flask, current_app, g
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

ENGINE_KEY = "levels_database_engine"
SESSION_FACTORY_KEY = "levels_session_factory"


def engine_configuration(
    database_url: str, turso_auth_token: str | None = None
) -> tuple[str, dict[str, object]]:
    connect_args: dict[str, object] = {}
    if database_url.startswith("libsql://"):
        if turso_auth_token is None:
            raise ValueError("A Turso auth token is required for a libsql database URL")
        database_url = f"sqlite+{database_url}"
        separator = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{separator}secure=true"
        connect_args["auth_token"] = turso_auth_token
    elif database_url.startswith("sqlite:///") and not database_url.startswith(
        "sqlite+pysqlite:///"
    ):
        database_url = database_url.replace("sqlite:///", "sqlite+pysqlite:///", 1)
    return database_url, connect_args


def create_database_engine(database_url: str, turso_auth_token: str | None = None) -> Engine:
    resolved_url, connect_args = engine_configuration(database_url, turso_auth_token)
    return create_engine(resolved_url, connect_args=connect_args, pool_pre_ping=True)


def init_database(app: Flask) -> None:
    engine = create_database_engine(
        cast(str, app.config["DATABASE_URL"]),
        cast(str | None, app.config["TURSO_AUTH_TOKEN"]),
    )
    app.extensions[ENGINE_KEY] = engine
    app.extensions[SESSION_FACTORY_KEY] = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False
    )
    app.teardown_appcontext(_close_request_session)


def get_engine() -> Engine:
    return cast(Engine, current_app.extensions[ENGINE_KEY])


def get_db() -> Session:
    session = g.get("database_session")
    if session is None:
        factory = cast(sessionmaker[Session], current_app.extensions[SESSION_FACTORY_KEY])
        session = factory()
        g.database_session = session
    return cast(Session, session)


def _close_request_session(_: BaseException | None = None) -> None:
    session = g.pop("database_session", None)
    if session is not None:
        session.close()


@contextmanager
def transaction() -> Iterator[Session]:
    session = get_db()
    try:
        # Authentication performs a tenant lookup before protected handlers run, which
        # starts SQLAlchemy's implicit transaction. Commit that request transaction here
        # instead of attempting a nested ``begin()``.
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
