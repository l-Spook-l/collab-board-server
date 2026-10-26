"""create saved boards and board members

Revision ID: 4f1e8a20c7bd
Revises: 9c1bc825f132
Create Date: 2026-10-25 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "4f1e8a20c7bd"
down_revision: str | Sequence[str] | None = "9c1bc825f132"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "board_table",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("document", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["user_table.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_board_table_owner_id", "board_table", ["owner_id"])

    op.create_table(
        "board_member_table",
        sa.Column("board_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("invited_by_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["board_id"], ["board_table.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by_id"], ["user_table.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user_table.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("board_id", "user_id"),
    )
    op.create_index(
        "ix_board_member_table_user_id",
        "board_member_table",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_board_member_table_user_id", table_name="board_member_table")
    op.drop_table("board_member_table")
    op.drop_index("ix_board_table_owner_id", table_name="board_table")
    op.drop_table("board_table")
