"""create entities table

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-22 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    entity_type_enum = postgresql.ENUM(
        "RESTAURANT",
        "HOTEL",
        name="entity_type",
    )

    op.create_table(
        "entities",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "type",
            entity_type_enum,
            nullable=False,
        ),
        sa.Column(
            "google_review_url",
            sa.String(length=1000),
            nullable=False,
        ),
        sa.Column(
            "slug",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_unique_constraint(
        "uq_entities_slug",
        "entities",
        ["slug"],
    )

    op.create_index(
        "ix_entities_slug",
        "entities",
        ["slug"],
        unique=False,
    )

    op.create_index(
        "ix_entities_type",
        "entities",
        ["type"],
        unique=False,
    )

    op.create_index(
        "ix_entities_is_active",
        "entities",
        ["is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_entities_is_active",
        table_name="entities",
    )

    op.drop_index(
        "ix_entities_type",
        table_name="entities",
    )

    op.drop_index(
        "ix_entities_slug",
        table_name="entities",
    )

    op.drop_constraint(
        "uq_entities_slug",
        "entities",
        type_="unique",
    )

    op.drop_table("entities")

    entity_type_enum = postgresql.ENUM(
        "RESTAURANT",
        "HOTEL",
        name="entity_type",
    )

    entity_type_enum.drop(
        op.get_bind(),
        checkfirst=True,
    )