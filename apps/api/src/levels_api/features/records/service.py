from __future__ import annotations

from sqlalchemy.orm import Session

from levels_api.features.profile.service import require_profile
from levels_api.schemas.serializers import serialize_personal_record

from . import repository


def list_record_payloads(
    session: Session,
    *,
    exercise_id: str | None,
    current_only: bool,
    owner: bool,
) -> list[dict[str, object]]:
    profile = require_profile(session)
    assert profile.visibility is not None
    if not owner and not profile.visibility.show_personal_records:
        return []
    return [
        serialize_personal_record(record)
        for record in repository.records(
            session,
            exercise_id=exercise_id,
            current_only=current_only,
            owner=owner,
        )
    ]
