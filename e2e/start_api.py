from __future__ import annotations

import os
import secrets
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from alembic import command
from alembic.config import Config
from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.orm import Session

from levels_api import create_app
from levels_api.database import create_database_engine
from levels_api.models import (
    ScheduleState,
    SessionStatus,
    Split,
    SplitDay,
    User,
    UserRole,
    UserStatus,
    WorkoutSession,
)
from levels_api.seed import seed_database, seed_user_starter

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "apps" / "api"
E2E_EMAIL = os.getenv("LEVELS_E2E_EMAIL", "member@levels-e2e.invalid")
E2E_PASSWORD = os.getenv("LEVELS_E2E_PASSWORD", "levels-e2e-password")


def prepare_database(database_url: str) -> None:
    config = Config(API_ROOT / "alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    seed_database(database_url)

    engine = create_database_engine(database_url)
    try:
        with Session(engine) as session, session.begin():
            member = User(
                email_normalized=E2E_EMAIL.strip().casefold(),
                password_hash=PasswordHasher().hash(E2E_PASSWORD),
                status=UserStatus.ACTIVE,
                role=UserRole.MEMBER,
                token_version=0,
                is_demo=False,
            )
            session.add(member)
            session.flush()
            seed_user_starter(session, member, display_name="Seeded E2E Member")

            active_split = session.scalar(
                select(Split).where(
                    Split.user_id == member.id,
                    Split.is_active.is_(True),
                    Split.archived_at.is_(None),
                )
            )
            assert active_split is not None
            days = session.scalars(
                select(SplitDay)
                .where(SplitDay.split_id == active_split.id)
                .order_by(SplitDay.sequence)
            ).all()
            lower_a = next(
                (day for day in days if day.name.startswith("Lower A")), None
            )
            assert lower_a is not None

            local_today = datetime.now(ZoneInfo("America/Toronto")).date()
            schedule = session.get(ScheduleState, member.id)
            assert schedule is not None
            schedule.cursor_split_day_id = lower_a.id
            schedule.cursor_effective_date = local_today
            schedule.version = 0

            # A deterministic pre-existing streak makes aura and reduced-motion checks meaningful.
            for offset in (3, 2, 1):
                occurred = datetime.combine(
                    local_today - timedelta(days=offset),
                    datetime.min.time(),
                    tzinfo=UTC,
                ) + timedelta(hours=18)
                session.add(
                    WorkoutSession(
                        user_id=member.id,
                        split_day_id=lower_a.id,
                        session_date_local=local_today - timedelta(days=offset),
                        started_at=occurred,
                        completed_at=occurred + timedelta(hours=1),
                        status=SessionStatus.COMPLETED,
                        title=f"Streak fixture {offset}",
                    )
                )
    finally:
        engine.dispose()


def main() -> None:
    web_origin = os.getenv("LEVELS_E2E_WEB_ORIGIN", "http://127.0.0.1:4173")
    with tempfile.TemporaryDirectory(prefix="levels-playwright-") as directory:
        database_path = Path(directory) / "levels-playwright.db"
        database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
        os.environ.update(
            {
                "APP_ENV": "production",
                "APP_TIMEZONE": "America/Toronto",
                "DATABASE_URL": database_url,
                "JWT_SECRET_KEY": secrets.token_urlsafe(48),
                "REGISTRATION_ENABLED": "true",
                "CORS_ALLOWED_ORIGINS": web_origin,
                "PUBLIC_WEB_ORIGIN": web_origin,
                "LOG_LEVEL": "WARNING",
            }
        )
        prepare_database(database_url)
        create_app().run(
            host="127.0.0.1",
            port=8000,
            debug=False,
            use_reloader=False,
            threaded=True,
        )


if __name__ == "__main__":
    main()
