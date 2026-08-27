"""Create/read internal risk escalation tickets."""

from __future__ import annotations

from uuid import UUID

from app.db.session import SessionLocal
from app.models.risk_escalation import RiskEscalation


async def create_risk_escalation(
    *,
    tenant_id: UUID,
    company_query: str,
    risk_level: str,
    summary: str,
) -> RiskEscalation:
    async with SessionLocal() as session:
        row = RiskEscalation(
            tenant_id=tenant_id,
            company_query=(company_query or "unknown").strip()[:255],
            risk_level=(risk_level or "medium").strip()[:32],
            summary=(summary or "").strip() or "Risk escalation",
            status="open",
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row
