from __future__ import annotations

from sqlalchemy.orm import Session

from levels_api.schemas.serializers import serialize_personal_record

from . import repository


def list_record_payloads(
    session: Session,
    user_id: str,
    *,
    exercise_id: str | None,
    current_only: bool,
) -> list[dict[str, object]]:
    return [
        serialize_personal_record(record)
        for record in repository.records(
            session,
            user_id,
            exercise_id=exercise_id,
            current_only=current_only,
        )
    ]
