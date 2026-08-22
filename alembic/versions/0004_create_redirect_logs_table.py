"""create redirect_logs table

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-22 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "redirect_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
    )

    op.create_index("ix_redirect_logs_entity_id", "redirect_logs", ["entity_id"], unique=False)
    op.create_index("ix_redirect_logs_created_at", "redirect_logs", ["created_at"], unique=False)
    op.create_index(
        "ix_redirect_logs_entity_id_created_at",
        "redirect_logs",
        ["entity_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_redirect_logs_entity_id_created_at", table_name="redirect_logs")
    op.drop_index("ix_redirect_logs_created_at", table_name="redirect_logs")
    op.drop_index("ix_redirect_logs_entity_id", table_name="redirect_logs")
    op.drop_table("redirect_logs")