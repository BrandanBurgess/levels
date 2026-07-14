from __future__ import annotations

import csv
import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from io import StringIO
from typing import Any

from sqlalchemy import Table, select
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


def _table_rows(session: Session, table: Table) -> list[dict[str, Any]]:
    return [
        {column: _json_value(value) for column, value in row.items()}
        for row in session.execute(select(table)).mappings()
    ]


def export_payload(session: Session, *, exported_at: datetime, version: str) -> dict[str, Any]:
    return {
        "exported_at": exported_at.isoformat(),
        "schema_version": version,
        "tables": {
            table.name: _table_rows(session, table) for table in Base.metadata.sorted_tables
        },
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
