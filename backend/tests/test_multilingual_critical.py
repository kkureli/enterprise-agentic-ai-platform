"""Critical Sprint 1 multilingual contracts (CI-safe, no live LLM)."""

from __future__ import annotations

import json
from pathlib import Path

from app.agents.mcp_tool_node import SYSTEM_PROMPT as MCP_SYSTEM_PROMPT
from app.agents.mcp_tool_node import _query_has_write_intent
from app.agents.router import PLANNER_SYSTEM_PROMPT
from app.agents.synthesis_node import SYNTHESIS_SYSTEM_PROMPT
from app.services.language_detection import (
    detect_response_language,
    format_response_language_instruction,
)
from app.services.query_expansion_service import SYSTEM_PROMPT as EXPANSION_SYSTEM_PROMPT
from app.services.rag_service import SYSTEM_PROMPT as RAG_SYSTEM_PROMPT
from app.services.sql_agent_service import SYSTEM_PROMPT as SQL_ANSWER_SYSTEM_PROMPT
from app.services.sql_generation_service import SYSTEM_PROMPT as SQL_GENERATION_SYSTEM_PROMPT

GOLDEN_DATASET_PATH = (
    Path(__file__).resolve().parents[2] / "evals" / "agent" / "golden_dataset.json"
)


def test_detects_turkish_and_english_questions() -> None:
    assert detect_response_language("AX-4317 hata kodu ne anlama geliyor?") == "tr"
    assert detect_response_language("MACHINE-42 için kaç bakım kaydı var?") == "tr"
    assert detect_response_language("What does error code AX-4317 mean?") == "en"
    assert detect_response_language("How many maintenance records does MACHINE-42 have?") == "en"


def test_turkish_write_intent_and_read_status() -> None:
    assert _query_has_write_intent(
        "MACHINE-42 için hidrolik basınç kaybı nedeniyle yüksek öncelikli bakım kaydı oluştur."
    )
    assert not _query_has_write_intent("MACHINE-42'nin güncel operasyonel durumu nedir?")


def test_response_language_instruction_helper() -> None:
    assert format_response_language_instruction("tr") == "Response language: Turkish (tr)."
    assert format_response_language_instruction("en") == "Response language: English (en)."


def test_capability_prompts_declare_bilingual_behavior() -> None:
    assert "English or Turkish" in PLANNER_SYSTEM_PROMPT
    assert "English or Turkish" in SQL_GENERATION_SYSTEM_PROMPT
    assert "English alternative" in EXPANSION_SYSTEM_PROMPT
    assert "English or Turkish" in MCP_SYSTEM_PROMPT
    assert "requested response language" in SYNTHESIS_SYSTEM_PROMPT
    assert "requested response language" in SQL_ANSWER_SYSTEM_PROMPT
    assert "requested response language" in RAG_SYSTEM_PROMPT


def test_golden_dataset_includes_critical_turkish_cases() -> None:
    dataset = json.loads(GOLDEN_DATASET_PATH.read_text(encoding="utf-8"))
    by_id = {case["id"]: case for case in dataset}

    required = {
        "knowledge_tr_01": ("knowledge", False),
        "sql_tr_01": ("sql", False),
        "tool_tr_01": ("tool", False),
        "tool_tr_write_01": ("tool", True),
        "unsupported_tr_01": ("unsupported", False),
        "composite_rag_mcp_tr_01": ("knowledge", False),
        "a2a_external_risk_tr_01": ("external_risk_assessment", False),
        "sql_company_tr_01": ("sql", False),
    }

    for case_id, (expected_route, expected_approval) in required.items():
        assert case_id in by_id, f"missing golden case {case_id}"
        case = by_id[case_id]
        assert case["expected_route"] == expected_route
        assert case["expected_approval"] is expected_approval
        assert detect_response_language(case["question"]) == "tr"

    composite = by_id["composite_rag_mcp_tr_01"]
    assert composite["expected_routes"] == ["knowledge", "tool"]
    assert by_id["composite_a2a_company_tr_01"]["expected_routes"] == [
        "sql",
        "knowledge",
        "external_risk_assessment",
    ]
