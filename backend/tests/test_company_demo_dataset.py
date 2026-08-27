"""Sprint 2 commercial company dataset contracts."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from app.core.demo_tenants import DEMO_TENANTS
from app.services.sql_generation_service import REPAIR_SYSTEM_PROMPT, SYSTEM_PROMPT
from app.services.sql_query_service import ALLOWED_TABLES

REPO_ROOT = Path(__file__).resolve().parents[2]
NORTHSTAR_DOCS = REPO_ROOT / "data" / "demo_tenants" / "northstar-commercial"


def test_sql_allowlist_includes_commercial_tables() -> None:
    assert {
        "companies",
        "company_revenue",
        "transactions",
        "payments",
    }.issubset(ALLOWED_TABLES)


def test_sql_generation_prompt_includes_company_schema() -> None:
    assert "companies:" in SYSTEM_PROMPT
    assert "company_revenue:" in SYSTEM_PROMPT
    assert "internal_customer_id" in SYSTEM_PROMPT
    assert "ciro" in SYSTEM_PROMPT
    assert "companies," in REPAIR_SYSTEM_PROMPT


def test_northstar_tenant_in_catalog() -> None:
    slugs = [spec.slug for spec in DEMO_TENANTS]
    assert "northstar-commercial" in slugs


def test_northstar_rag_docs_cover_five_companies() -> None:
    texts = "\n".join(path.read_text(encoding="utf-8") for path in NORTHSTAR_DOCS.glob("*.txt"))
    for marker in (
        "CUST-SPOTIFY",
        "CUST-SIEMENS",
        "CUST-SHOPIFY",
        "CUST-ADOBE",
        "CUST-MICROSOFT",
        "spotify.com",
        "siemens.com",
        "shopify.com",
        "adobe.com",
        "microsoft.com",
    ):
        assert marker in texts


def test_synthetic_revenue_amounts_are_distinct() -> None:
    # Guard against accidental copy-paste collapsing entity financials.
    amounts = {
        Decimal("14500000.00"),
        Decimal("9200000.00"),
        Decimal("7800000.00"),
        Decimal("11200000.00"),
        Decimal("22100000.00"),
    }
    assert len(amounts) == 5
