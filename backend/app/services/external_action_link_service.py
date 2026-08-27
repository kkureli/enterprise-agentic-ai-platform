"""Persist and look up external action audit/link rows (GitHub Issues, etc.)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.external_action_link import ExternalActionLink


async def find_external_action_link(
    *,
    tenant_id: UUID,
    dedupe_key: str,
) -> ExternalActionLink | None:
    key = dedupe_key.strip()
    if not key:
        return None
    async with SessionLocal() as session:
        return await session.scalar(
            select(ExternalActionLink).where(
                ExternalActionLink.tenant_id == tenant_id,
                ExternalActionLink.dedupe_key == key,
            )
        )


async def create_external_action_link(
    *,
    tenant_id: UUID,
    provider: str,
    external_id: str,
    external_url: str,
    action_type: str,
    status: str,
    dedupe_key: str,
    internal_ticket_id: UUID | None = None,
    risk_escalation_id: UUID | None = None,
    company_query: str | None = None,
) -> ExternalActionLink:
    async with SessionLocal() as session:
        row = ExternalActionLink(
            tenant_id=tenant_id,
            internal_ticket_id=internal_ticket_id,
            risk_escalation_id=risk_escalation_id,
            provider=provider,
            external_id=str(external_id),
            external_url=external_url,
            action_type=action_type,
            status=status,
            dedupe_key=dedupe_key.strip(),
            company_query=company_query,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row
