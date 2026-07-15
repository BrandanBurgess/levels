from __future__ import annotations

import csv
import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from io import StringIO
from typing import Any

from sqlalchemy import ColumnElement, Table, select
from sqlalchemy.orm import Session

from levels_api.models import Base


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, bytes):
        return value.hex()
    return value


def _table_rows(
    session: Session, table: Table, predicate: ColumnElement[bool]
) -> list[dict[str, Any]]:
    return [
        {column: _json_value(value) for column, value in row.items()}
        for row in session.execute(select(table).where(predicate)).mappings()
    ]


def _ids(rows: list[dict[str, Any]], column: str = "id") -> set[str]:
    return {str(row[column]) for row in rows}


def export_payload(
    session: Session, user_id: str, *, exported_at: datetime, version: str
) -> dict[str, Any]:
    tables = Base.metadata.tables
    exported: dict[str, list[dict[str, Any]]] = {}

    for name in (
        "profiles",
        "splits",
        "workout_sessions",
        "readiness_logs",
        "water_logs",
        "personal_records",
        "achievements",
        "progression_suggestions",
        "schedule_state",
        "daily_plan_overrides",
        "daily_exercise_plans",
        "avatar_settings",
        "command_receipts",
    ):
        table = tables[name]
        exported[name] = _table_rows(session, table, table.c.user_id == user_id)

    profile_ids = _ids(exported["profiles"])
    split_ids = _ids(exported["splits"])
    session_ids = _ids(exported["workout_sessions"])
    plan_ids = _ids(exported["daily_exercise_plans"])

    for name in ("visibility_settings", "app_settings"):
        table = tables[name]
        exported[name] = _table_rows(session, table, table.c.profile_id.in_(profile_ids))

    split_days = tables["split_days"]
    exported["split_days"] = _table_rows(
        session, split_days, split_days.c.split_id.in_(split_ids)
    )
    split_day_ids = _ids(exported["split_days"])

    template_items = tables["workout_template_items"]
    exported["workout_template_items"] = _table_rows(
        session, template_items, template_items.c.split_day_id.in_(split_day_ids)
    )
    template_item_ids = _ids(exported["workout_template_items"])
    alternatives = tables["template_alternatives"]
    exported["template_alternatives"] = _table_rows(
        session, alternatives, alternatives.c.template_item_id.in_(template_item_ids)
    )

    session_exercises = tables["session_exercises"]
    exported["session_exercises"] = _table_rows(
        session,
        session_exercises,
        session_exercises.c.workout_session_id.in_(session_ids),
    )
    session_exercise_ids = _ids(exported["session_exercises"])
    set_logs = tables["set_logs"]
    exported["set_logs"] = _table_rows(
        session, set_logs, set_logs.c.session_exercise_id.in_(session_exercise_ids)
    )

    daily_items = tables["daily_exercise_plan_items"]
    exported["daily_exercise_plan_items"] = _table_rows(
        session, daily_items, daily_items.c.daily_exercise_plan_id.in_(plan_ids)
    )

    exercises = tables["exercises"]
    exported["exercises"] = _table_rows(
        session,
        exercises,
        (exercises.c.owner_user_id.is_(None)) | (exercises.c.owner_user_id == user_id),
    )
    exercise_ids = _ids(exported["exercises"])
    exercise_muscles = tables["exercise_muscles"]
    exported["exercise_muscles"] = _table_rows(
        session, exercise_muscles, exercise_muscles.c.exercise_id.in_(exercise_ids)
    )
    muscle_groups = tables["muscle_groups"]
    exported["muscle_groups"] = _table_rows(session, muscle_groups, muscle_groups.c.id.in_({
        str(row["muscle_group_id"]) for row in exported["exercise_muscles"]
    }))

    return {
        "exported_at": exported_at.isoformat(),
        "schema_version": version,
        "tables": exported,
    }


def _csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list | dict):
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    else:
        text = str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{text}"
    return text


def export_csv(payload: dict[str, Any]) -> str:
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(["table", "row", "column", "value"])
    tables = payload["tables"]
    assert isinstance(tables, dict)
    for table_name, rows in tables.items():
        assert isinstance(rows, list)
        for row_number, row in enumerate(rows, start=1):
            assert isinstance(row, dict)
            for column, value in row.items():
                writer.writerow([table_name, row_number, column, _csv_cell(value)])
    return output.getvalue()
