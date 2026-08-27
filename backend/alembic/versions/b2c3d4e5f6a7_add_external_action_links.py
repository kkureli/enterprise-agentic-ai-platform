"""add external_action_links audit table for GitHub MCP writes

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-27 18:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "external_action_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("internal_ticket_id", sa.UUID(), nullable=True),
        sa.Column(
            "provider",
            sa.String(length=32),
            server_default="github",
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("external_url", sa.Text(), nullable=False),
        sa.Column(
            "action_type",
            sa.String(length=64),
            server_default="create_issue",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="open",
            nullable=False,
        ),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("company_query", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["internal_ticket_id"],
            ["maintenance_tickets.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "dedupe_key",
            name="uq_external_action_links_tenant_dedupe_key",
        ),
    )
    op.create_index(
        op.f("ix_external_action_links_tenant_id"),
        "external_action_links",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_external_action_links_internal_ticket_id"),
        "external_action_links",
        ["internal_ticket_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_external_action_links_internal_ticket_id"),
        table_name="external_action_links",
    )
    op.drop_index(
        op.f("ix_external_action_links_tenant_id"),
        table_name="external_action_links",
    )
    op.drop_table("external_action_links")
