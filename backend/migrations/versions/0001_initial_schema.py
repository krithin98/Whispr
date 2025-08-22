"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2024-01-01 00:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ts", sa.Text, nullable=False),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("payload", sa.Text),
    )

    op.create_table(
        "rules",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("trigger_expr", sa.Text, nullable=False),
        sa.Column("prompt_tpl", sa.Text, nullable=False),
        sa.Column("is_active", sa.Integer, nullable=False, server_default="1"),
    )

    op.create_table(
        "strategies",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("is_active", sa.Integer, nullable=False, server_default="1"),
    )

    op.create_table(
        "indicator_data",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ts", sa.Text, nullable=False),
        sa.Column("indicator_name", sa.Text, nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("metadata", sa.Text),
    )

def downgrade() -> None:
    op.drop_table("indicator_data")
    op.drop_table("strategies")
    op.drop_table("rules")
    op.drop_table("events")
