"""add water idempotency key

Revision ID: 7a6e13e4cd9b
Revises: 2b3603691cea
Create Date: 2026-07-13 21:52:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7a6e13e4cd9b"
down_revision: str | None = "2b3603691cea"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("water_logs") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=128), nullable=True))
        batch_op.create_unique_constraint("uq_water_logs_idempotency_key", ["idempotency_key"])


def downgrade() -> None:
    with op.batch_alter_table("water_logs") as batch_op:
        batch_op.drop_constraint("uq_water_logs_idempotency_key", type_="unique")
        batch_op.drop_column("idempotency_key")
