"""create subscriptions table

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-22 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    subscription_status_enum = postgresql.ENUM(
        "ACTIVE", "EXPIRED", "CANCELLED", name="subscription_status",
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", subscription_status_enum, nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_subscriptions_entity_id", "subscriptions", ["entity_id"], unique=False)
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"], unique=False)
    # Composite index to speed up the redirect endpoint's hot-path lookup.
    op.create_index(
        "ix_subscriptions_entity_id_created_at",
        "subscriptions",
        ["entity_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_subscriptions_entity_id_created_at", table_name="subscriptions")
    op.drop_index("ix_subscriptions_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_entity_id", table_name="subscriptions")
    op.drop_table("subscriptions")

    subscription_status_enum = postgresql.ENUM(
        "ACTIVE", "EXPIRED", "CANCELLED", name="subscription_status",
    )
    subscription_status_enum.drop(op.get_bind(), checkfirst=True)