"""Initial schema: users, analysis_sessions, products, reports

Revision ID: 001
Revises:
Create Date: 2026-06-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "analysis_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'processing'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("files_meta", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('processing', 'done', 'failed')", name="ck_session_status"
        ),
    )
    op.create_index("ix_analysis_sessions_user_id", "analysis_sessions", ["user_id"])

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("article", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("purchase_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("sale_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("weight", sa.Numeric(8, 3), nullable=False),
        sa.Column("sold", sa.Integer(), nullable=False),
        sa.Column("returns", sa.Integer(), nullable=False),
        sa.Column("net_revenue", sa.Numeric(16, 2), nullable=False),
        sa.Column("commission", sa.Numeric(16, 2), nullable=False),
        sa.Column("logistics_total", sa.Numeric(16, 2), nullable=False),
        sa.Column("purchase_cost", sa.Numeric(16, 2), nullable=False),
        sa.Column("profit", sa.Numeric(16, 2), nullable=False),
        sa.Column("margin_pct", sa.Numeric(8, 2), nullable=False),
        sa.Column("margin_zone", sa.String(10), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"], ["analysis_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "margin_zone IN ('green', 'yellow', 'red')", name="ck_margin_zone"
        ),
    )
    op.create_index("ix_products_session_id", "products", ["session_id"])

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("ai_interpretation", sa.Text(), nullable=True),
        sa.Column(
            "chat_history", sa.JSON(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["analysis_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_reports_session_id"),
    )


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_index("ix_products_session_id", table_name="products")
    op.drop_table("products")
    op.drop_index("ix_analysis_sessions_user_id", table_name="analysis_sessions")
    op.drop_table("analysis_sessions")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
