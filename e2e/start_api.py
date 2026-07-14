from __future__ import annotations

import os
import secrets
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from alembic import command
from alembic.config import Config
from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.orm import Session

from levels_api import create_app
from levels_api.database import create_database_engine
from levels_api.models import Split, SplitDay
from levels_api.seed import seed_database

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "apps" / "api"
DATABASE_PATH = Path(tempfile.gettempdir()) / "levels-playwright.db"
E2E_PASSWORD = "levels-e2e-password"


def prepare_database(database_url: str) -> None:
    DATABASE_PATH.unlink(missing_ok=True)
    config = Config(API_ROOT / "alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    seed_database(database_url)

    engine = create_database_engine(database_url)
    try:
        with Session(engine) as session, session.begin():
            active_split = session.scalar(
                select(Split).where(Split.is_active.is_(True))
            )
            assert active_split is not None
            days = session.scalars(
                select(SplitDay)
                .where(SplitDay.split_id == active_split.id)
                .order_by(SplitDay.sequence)
            ).all()
            assert days
            today = datetime.now(ZoneInfo("America/Toronto")).weekday()
            for day in days:
                if day.recommended_weekday == today:
                    day.recommended_weekday = None
            days[0].recommended_weekday = today
    finally:
        engine.dispose()


def main() -> None:
    database_url = f"sqlite+pysqlite:///{DATABASE_PATH.as_posix()}"
    web_origin = os.getenv("LEVELS_E2E_WEB_ORIGIN", "http://127.0.0.1:4173")
    os.environ.update(
        {
            "APP_ENV": "production",
            "APP_TIMEZONE": "America/Toronto",
            "DATABASE_URL": database_url,
            "ADMIN_USERNAME": "brandan",
            "ADMIN_PASSWORD_HASH": PasswordHasher().hash(E2E_PASSWORD),
            "JWT_SECRET_KEY": secrets.token_urlsafe(48),
            "CORS_ALLOWED_ORIGINS": web_origin,
            "PUBLIC_WEB_ORIGIN": web_origin,
            "LOG_LEVEL": "WARNING",
        }
    )
    prepare_database(database_url)
    create_app().run(
        host="127.0.0.1", port=8000, debug=False, use_reloader=False, threaded=True
    )


if __name__ == "__main__":
    main()
