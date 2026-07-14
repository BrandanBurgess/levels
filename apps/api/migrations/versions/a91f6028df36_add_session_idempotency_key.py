"""add session idempotency key

Revision ID: a91f6028df36
Revises: 7a6e13e4cd9b
Create Date: 2026-07-13 22:55:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a91f6028df36"
down_revision: str | None = "7a6e13e4cd9b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("workout_sessions") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=128), nullable=True))
        batch_op.create_unique_constraint(
            "uq_workout_sessions_idempotency_key", ["idempotency_key"]
        )


def downgrade() -> None:
    with op.batch_alter_table("workout_sessions") as batch_op:
        batch_op.drop_constraint("uq_workout_sessions_idempotency_key", type_="unique")
        batch_op.drop_column("idempotency_key")
