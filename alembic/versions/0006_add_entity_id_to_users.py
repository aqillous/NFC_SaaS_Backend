"""add entity_id to users for restaurant dashboard accounts

Revision ID: 0006
Revises: 0005
"""

from typing import (
    Sequence,
    Union,
)

from alembic import op

import sqlalchemy as sa

from sqlalchemy.dialects import postgresql


revision: str = "0006"

down_revision: Union[
    str,
    None
] = "0005"

branch_labels: Union[
    str,
    Sequence[str],
    None
] = None

depends_on: Union[
    str,
    Sequence[str],
    None
] = None


def upgrade() -> None:

    op.add_column(
        "users",

        sa.Column(
            "entity_id",

            postgresql.UUID(
                as_uuid=True
            ),

            sa.ForeignKey(
                "entities.id",
                ondelete="SET NULL",
            ),

            nullable=True,
        ),
    )


    op.create_index(
        "ix_users_entity_id",
        "users",
        ["entity_id"],
        unique=False,
    )


def downgrade() -> None:

    op.drop_index(
        "ix_users_entity_id",
        table_name="users",
    )

    op.drop_column(
        "users",
        "entity_id",
    )