"""add risk_escalations + link column for A2A internal tickets

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-27 19:25:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "risk_escalations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("company_query", sa.String(length=255), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="open",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_risk_escalations_tenant_id"),
        "risk_escalations",
        ["tenant_id"],
        unique=False,
    )
    op.add_column(
        "external_action_links",
        sa.Column("risk_escalation_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        op.f("ix_external_action_links_risk_escalation_id"),
        "external_action_links",
        ["risk_escalation_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_external_action_links_risk_escalation_id",
        "external_action_links",
        "risk_escalations",
        ["risk_escalation_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_external_action_links_risk_escalation_id",
        "external_action_links",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_external_action_links_risk_escalation_id"),
        table_name="external_action_links",
    )
    op.drop_column("external_action_links", "risk_escalation_id")
    op.drop_index(op.f("ix_risk_escalations_tenant_id"), table_name="risk_escalations")
    op.drop_table("risk_escalations")
