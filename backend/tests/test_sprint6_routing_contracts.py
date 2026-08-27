"""Sprint 6 routing contract checks (no live LLM)."""

from __future__ import annotations

import json
from pathlib import Path

from app.agents.router import PLANNER_SYSTEM_PROMPT, READ_ROUTES, normalize_planned_routes

GOLDEN_PATH = (
    Path(__file__).resolve().parents[2] / "evals" / "agent" / "golden_dataset.json"
)


def test_read_routes_include_external_risk() -> None:
    assert "external_risk_assessment" in READ_ROUTES


def test_planner_prompt_keeps_internal_sql_off_a2a() -> None:
    assert '→ routes=["sql"]' in PLANNER_SYSTEM_PROMPT
    assert "What is Spotify's annual revenue?" in PLANNER_SYSTEM_PROMPT
    assert "Do NOT select external_risk_assessment for simple internal revenue" in (
        PLANNER_SYSTEM_PROMPT
    )


def test_planner_prompt_routes_external_investigation_to_a2a() -> None:
    assert "Assess Microsoft external risks." in PLANNER_SYSTEM_PROMPT
    assert '→ routes=["external_risk_assessment"]' in PLANNER_SYSTEM_PROMPT


def test_planner_prompt_full_risk_is_composite() -> None:
    assert (
        '→ routes=["sql","knowledge","external_risk_assessment"]'
        in PLANNER_SYSTEM_PROMPT
    )


def test_golden_routing_contracts() -> None:
    cases = {row["id"]: row for row in json.loads(GOLDEN_PATH.read_text())}

    # Simple internal commercial → SQL only (not A2A).
    sql = cases["sql_company_01"]
    assert sql["expected_route"] == "sql"
    assert "external_risk_assessment" not in (sql.get("expected_routes") or [sql["expected_route"]])

    # External investigation → A2A.
    a2a = cases["a2a_external_risk_01"]
    assert a2a["expected_route"] == "external_risk_assessment"

    # Full risk composite includes SQL + knowledge + A2A.
    composite = cases["composite_a2a_company_01"]
    assert set(composite["expected_routes"]) == {
        "sql",
        "knowledge",
        "external_risk_assessment",
    }

    # TR mirrors EN for A2A/composite.
    assert cases["a2a_external_risk_tr_01"]["expected_route"] == "external_risk_assessment"
    assert set(cases["composite_a2a_company_tr_01"]["expected_routes"]) == {
        "sql",
        "knowledge",
        "external_risk_assessment",
    }


def test_normalize_rejects_mixing_unsupported_with_a2a() -> None:
    assert normalize_planned_routes(["unsupported", "external_risk_assessment"]) == [
        "external_risk_assessment"
    ]
