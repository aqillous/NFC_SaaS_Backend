"""create feedback table

Revision ID: 0005
Revises: 0004
"""

from typing import (
    Sequence,
    Union,
)

from alembic import op

import sqlalchemy as sa

from sqlalchemy.dialects import postgresql


revision: str = "0005"

down_revision: Union[
    str,
    None
] = "0004"

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

    op.create_table(

        "feedback",

        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),

        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),

            sa.ForeignKey(
                "entities.id",
                ondelete="CASCADE",
            ),

            nullable=False,
        ),

        sa.Column(
            "quality",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "service",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "taste",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "overall_score",
            sa.Float(),
            nullable=False,
        ),

        sa.Column(
            "comment",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "redirected_to_google",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),

        sa.Column(
            "user_agent",
            sa.String(length=500),
            nullable=True,
        ),

        sa.Column(
            "ip_address",
            sa.String(length=45),
            nullable=True,
        ),

        sa.CheckConstraint(
            "quality BETWEEN 1 AND 5",
            name="ck_feedback_quality",
        ),

        sa.CheckConstraint(
            "service BETWEEN 1 AND 5",
            name="ck_feedback_service",
        ),

        sa.CheckConstraint(
            "taste BETWEEN 1 AND 5",
            name="ck_feedback_taste",
        ),

        sa.CheckConstraint(
            "overall_score >= 1 AND overall_score <= 5",
            name="ck_feedback_overall",
        ),
    )


    op.create_index(
        "ix_feedback_entity_id",
        "feedback",
        ["entity_id"],
        unique=False,
    )


    op.create_index(
        "ix_feedback_created_at",
        "feedback",
        ["created_at"],
        unique=False,
    )


    op.create_index(
        "ix_feedback_redirected_to_google",
        "feedback",
        ["redirected_to_google"],
        unique=False,
    )


    op.create_index(
        "ix_feedback_entity_created_at",
        "feedback",
        ["entity_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:

    op.drop_index(
        "ix_feedback_entity_created_at",
        table_name="feedback",
    )

    op.drop_index(
        "ix_feedback_redirected_to_google",
        table_name="feedback",
    )

    op.drop_index(
        "ix_feedback_created_at",
        table_name="feedback",
    )

    op.drop_index(
        "ix_feedback_entity_id",
        table_name="feedback",
    )

    op.drop_table(
        "feedback"
    )