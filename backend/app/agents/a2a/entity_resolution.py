"""Resolve commercial company entities from tenant-scoped SQL data."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.agents.a2a.schemas import EntityResolution
from app.db.session import SessionLocal
from app.models.company import Company


def _normalize(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _alias_list(aliases: str | None) -> list[str]:
    if not aliases:
        return []
    return [part.strip() for part in aliases.split(",") if part.strip()]


def resolve_company_row(company: Company, query: str) -> EntityResolution | None:
    """Return entity resolution when query uniquely matches this company row."""

    needle = _normalize(query)
    if not needle:
        return None

    candidates = {
        _normalize(company.company_name),
        _normalize(company.official_name),
        _normalize(company.domain),
        _normalize(company.internal_customer_id),
        *{_normalize(alias) for alias in _alias_list(company.aliases)},
    }
    # Also allow domain without TLD separators differences: spotify.com vs Spotify
    matched: list[str] = []
    for value in candidates:
        if not value:
            continue
        if needle == value or needle in value or value in needle:
            matched.append(value)

    if not matched:
        return None

    # Prefer exact identity hits over loose substring matches.
    exact_fields = {
        _normalize(company.company_name),
        _normalize(company.official_name),
        _normalize(company.domain),
        _normalize(company.internal_customer_id),
    }
    confidence = 0.98 if needle in exact_fields else 0.85

    return EntityResolution(
        internal_customer_id=company.internal_customer_id,
        company_name=company.company_name,
        official_name=company.official_name,
        domain=company.domain,
        matched_aliases=[
            alias for alias in _alias_list(company.aliases) if _normalize(alias) in matched
        ],
        resolution_confidence=confidence,
        unresolved=False,
    )


async def resolve_company_entity(
    *,
    tenant_id: UUID,
    company_query: str,
) -> EntityResolution:
    """Resolve a company query against tenant companies; never guess across brands."""

    async with SessionLocal() as session:
        rows = (
            await session.execute(select(Company).where(Company.tenant_id == tenant_id))
        ).scalars().all()

    matches: list[EntityResolution] = []
    for row in rows:
        resolved = resolve_company_row(row, company_query)
        if resolved is not None:
            matches.append(resolved)

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        # Ambiguous match — do not pick a winner.
        return EntityResolution(
            unresolved=True,
            resolution_confidence=0.0,
            matched_aliases=[m.company_name or "" for m in matches if m.company_name],
        )

    return EntityResolution(unresolved=True, resolution_confidence=0.0)
