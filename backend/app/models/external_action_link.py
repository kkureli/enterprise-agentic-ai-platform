"""Audit/link metadata for external write actions (e.g. GitHub Issues).

GitHub remains source of truth for issue content; this table stores only link
metadata and dedupe keys so the same evaluation does not open duplicates.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExternalActionLink(Base):
    __tablename__ = "external_action_links"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "dedupe_key",
            name="uq_external_action_links_tenant_dedupe_key",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional link to an internal maintenance ticket when both are created.
    internal_ticket_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("maintenance_tickets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    provider: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="github",
        server_default="github",
    )

    external_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    external_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    action_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="create_issue",
        server_default="create_issue",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="open",
        server_default="open",
    )

    # Stable key to prevent duplicate GitHub issues for the same evaluation.
    dedupe_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    company_query: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
