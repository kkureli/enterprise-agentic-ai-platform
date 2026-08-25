"""Regression tests for SQL safety repair, MCP protocol, and tool_06 HITL."""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from app.agents.mcp_tool_node import (
    _query_has_write_intent,
    _tool_messages_for_protocol,
    mcp_tool_node,
)
from app.agents.synthesis_node import synthesis_node
from app.services.sql_agent_service import answer_with_sql
from app.services.sql_generation_service import (
    build_repair_human_message,
    extract_table_alias_pairs,
    required_tenant_predicates,
)
from app.services.sql_query_service import UnsafeSQLQueryError, validate_readonly_sql

# Modeled on composite_rag_sql_01 (RAG+SQL count of MACHINE-42 maintenance records).
COMPOSITE_RAG_SQL_01_QUESTION = (
    "What does AX-4317 mean, and how many maintenance records does MACHINE-42 have?"
)
COMPOSITE_RAG_SQL_01_INVALID_SQL = """
SELECT COUNT(mr.id) AS maintenance_record_count
FROM maintenance_records AS mr
JOIN assets AS a ON a.id = mr.asset_id
WHERE a.tenant_id = :tenant_id
  AND a.asset_code = 'MACHINE-42'
""".strip()
COMPOSITE_RAG_SQL_01_REPAIRED_SQL = """
SELECT COUNT(mr.id) AS maintenance_record_count
FROM maintenance_records AS mr
JOIN assets AS a ON a.id = mr.asset_id
WHERE a.tenant_id = :tenant_id
  AND mr.tenant_id = :tenant_id
  AND a.asset_code = 'MACHINE-42'
""".strip()
COMPOSITE_RAG_SQL_01_BAD_REPAIR_TABLE_NAME = """
SELECT COUNT(mr.id) AS maintenance_record_count
FROM maintenance_records AS mr
JOIN assets AS a ON a.id = mr.asset_id
WHERE a.tenant_id = :tenant_id
  AND maintenance_records.tenant_id = :tenant_id
  AND a.asset_code = 'MACHINE-42'
""".strip()

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def test_or_conditions_still_rejected_by_validator():
    with pytest.raises(UnsafeSQLQueryError, match="OR conditions"):
        validate_readonly_sql(
            """
            SELECT a.asset_code
            FROM assets AS a
            WHERE a.tenant_id = :tenant_id
              AND (a.asset_code = 'MACHINE-42' OR a.asset_code = 'MACHINE-17')
            """
        )


def test_join_missing_alias_tenant_still_rejected():
    with pytest.raises(UnsafeSQLQueryError, match="Every table in a join"):
        validate_readonly_sql(
            """
            SELECT mr.description
            FROM maintenance_records AS mr
            JOIN assets AS a ON a.id = mr.asset_id
            WHERE a.tenant_id = :tenant_id
              AND a.asset_code = 'MACHINE-42'
            """
        )


def test_compliant_join_passes_validator():
    validate_readonly_sql(
        """
        SELECT mr.description
        FROM maintenance_records AS mr
        JOIN assets AS a ON a.id = mr.asset_id
        WHERE a.tenant_id = :tenant_id
          AND mr.tenant_id = :tenant_id
          AND a.asset_code = 'MACHINE-42'
        """
    )


def test_table_name_tenant_filter_still_rejected_when_alias_exists():
    """Validator keys off aliases — bare table names do not satisfy join scoping."""

    with pytest.raises(UnsafeSQLQueryError, match=r"Missing tenant filter for: \['mr'\]"):
        validate_readonly_sql(COMPOSITE_RAG_SQL_01_BAD_REPAIR_TABLE_NAME)


def test_repair_context_lists_dynamic_alias_predicates_for_composite_rag_sql_01():
    pairs = extract_table_alias_pairs(COMPOSITE_RAG_SQL_01_INVALID_SQL)
    assert ("maintenance_records", "mr") in pairs
    assert ("assets", "a") in pairs

    predicates = required_tenant_predicates(COMPOSITE_RAG_SQL_01_INVALID_SQL)
    assert predicates == ["mr.tenant_id = :tenant_id", "a.tenant_id = :tenant_id"]

    with pytest.raises(UnsafeSQLQueryError, match=r"Missing tenant filter for: \['mr'\]") as exc:
        validate_readonly_sql(COMPOSITE_RAG_SQL_01_INVALID_SQL)

    message = build_repair_human_message(
        COMPOSITE_RAG_SQL_01_QUESTION,
        COMPOSITE_RAG_SQL_01_INVALID_SQL,
        str(exc.value),
    )
    assert "maintenance_records AS mr" in message
    assert "assets AS a" in message
    assert "mr.tenant_id = :tenant_id" in message
    assert "a.tenant_id = :tenant_id" in message
    assert "not only in JOIN ON" in message


@pytest.mark.asyncio
async def test_composite_rag_sql_01_invalid_join_repair_then_execute(monkeypatch):
    """composite_rag_sql_01 shape: invalid join → reject → alias repair → execute."""

    async def fake_generate(question: str) -> str:
        assert "AX-4317" in question
        assert "MACHINE-42" in question
        return COMPOSITE_RAG_SQL_01_INVALID_SQL

    async def fake_repair(question: str, rejected_sql: str, validation_error: str) -> str:
        assert rejected_sql == COMPOSITE_RAG_SQL_01_INVALID_SQL
        assert "Missing tenant filter" in validation_error
        # Mirror production repair context construction.
        context = build_repair_human_message(question, rejected_sql, validation_error)
        assert "mr.tenant_id = :tenant_id" in context
        assert "a.tenant_id = :tenant_id" in context
        # Bare table-name "repair" must remain invalid.
        with pytest.raises(UnsafeSQLQueryError, match="Missing tenant filter"):
            validate_readonly_sql(COMPOSITE_RAG_SQL_01_BAD_REPAIR_TABLE_NAME)
        return COMPOSITE_RAG_SQL_01_REPAIRED_SQL

    async def fake_execute(*, tenant_id, sql):
        validate_readonly_sql(sql)
        assert sql == COMPOSITE_RAG_SQL_01_REPAIRED_SQL
        return [{"maintenance_record_count": 2}]

    class FakeAnswer:
        content = "MACHINE-42 has 2 maintenance records."

    class FakeModel:
        async def ainvoke(self, messages):
            return FakeAnswer()

    monkeypatch.setattr("app.services.sql_agent_service.generate_sql", fake_generate)
    monkeypatch.setattr("app.services.sql_agent_service.repair_sql", fake_repair)
    monkeypatch.setattr("app.services.sql_agent_service.execute_readonly_sql", fake_execute)
    monkeypatch.setattr("app.services.sql_agent_service.get_chat_model", lambda: FakeModel())

    result = await answer_with_sql(
        tenant_id=uuid4(),
        question=COMPOSITE_RAG_SQL_01_QUESTION,
    )
    assert result.repaired is True
    assert result.sql == COMPOSITE_RAG_SQL_01_REPAIRED_SQL
    assert "mr.tenant_id = :tenant_id" in result.sql
    assert "a.tenant_id = :tenant_id" in result.sql
    validate_readonly_sql(result.sql)
    assert result.row_count == 1


@pytest.mark.asyncio
async def test_sql_repair_produces_tenant_safe_join(monkeypatch):
    async def fake_generate(question: str) -> str:
        return (
            "SELECT mr.description FROM maintenance_records AS mr "
            "JOIN assets AS a ON a.id = mr.asset_id "
            "WHERE a.tenant_id = :tenant_id AND a.asset_code = 'MACHINE-42'"
        )

    async def fake_repair(question: str, rejected_sql: str, validation_error: str) -> str:
        assert "Missing tenant filter" in validation_error
        assert "mr" in rejected_sql
        context = build_repair_human_message(question, rejected_sql, validation_error)
        assert "mr.tenant_id = :tenant_id" in context
        return (
            "SELECT mr.description FROM maintenance_records AS mr "
            "JOIN assets AS a ON a.id = mr.asset_id "
            "WHERE a.tenant_id = :tenant_id AND mr.tenant_id = :tenant_id "
            "AND a.asset_code = 'MACHINE-42'"
        )

    async def fake_execute(*, tenant_id, sql):
        validate_readonly_sql(sql)
        return [{"description": "Hydraulic pressure sensor inspected."}]

    class FakeAnswer:
        content = "MACHINE-42 has related maintenance history."

    class FakeModel:
        async def ainvoke(self, messages):
            return FakeAnswer()

    monkeypatch.setattr("app.services.sql_agent_service.generate_sql", fake_generate)
    monkeypatch.setattr("app.services.sql_agent_service.repair_sql", fake_repair)
    monkeypatch.setattr("app.services.sql_agent_service.execute_readonly_sql", fake_execute)
    monkeypatch.setattr("app.services.sql_agent_service.get_chat_model", lambda: FakeModel())

    result = await answer_with_sql(tenant_id=uuid4(), question="history for MACHINE-42")
    assert result.repaired is True
    assert "mr.tenant_id = :tenant_id" in result.sql
    validate_readonly_sql(result.sql)


def test_tool_messages_cover_all_tool_call_ids():
    request = AIMessage(
        content="",
        tool_calls=[
            {"name": "get_asset_status", "args": {"asset_id": "MACHINE-42"}, "id": "call_1"},
            {"name": "get_maintenance_history", "args": {"asset_id": "MACHINE-42"}, "id": "call_2"},
        ],
    )
    messages = _tool_messages_for_protocol(
        request,
        primary_id="call_1",
        primary_content='{"status":"warning"}',
    )
    assert {message.tool_call_id for message in messages} == {"call_1", "call_2"}
    assert messages[0].content == '{"status":"warning"}'
    assert "skipped" in messages[1].content


def test_write_intent_detects_tool_06_phrasing():
    assert _query_has_write_intent("Use the enterprise system to create a ticket for MACHINE-42.")
    assert not _query_has_write_intent("What is the current operational status of MACHINE-42?")


@pytest.mark.asyncio
async def test_tool_06_requires_approval(monkeypatch):
    class FakeTool:
        def __init__(self, name: str):
            self.name = name
            self.description = name
            self.input_schema = {"type": "object", "properties": {}}

    class FakeTools:
        tools = [
            FakeTool("get_asset_status"),
            FakeTool("create_maintenance_ticket"),
        ]

    class FakeModel:
        def bind_tools(self, schemas, **kwargs):
            return self

        async def ainvoke(self, messages):
            # Simulate a model that fails to emit tool_calls — write fallback must still HITL.
            return AIMessage(content="I will create a ticket.")

    async def fake_draft(query: str):
        from app.agents.mcp_tool_node import TicketDraft

        return TicketDraft(
            asset_code="MACHINE-42",
            issue="Maintenance ticket requested for MACHINE-42",
            priority="high",
        )

    async def fake_list_tools():
        return FakeTools()

    monkeypatch.setattr(
        "app.agents.mcp_tool_node.list_maintenance_tools",
        fake_list_tools,
    )
    monkeypatch.setattr("app.agents.mcp_tool_node.get_chat_model", lambda: FakeModel())
    monkeypatch.setattr("app.agents.mcp_tool_node._draft_ticket_from_query", fake_draft)

    result = await mcp_tool_node(
        {
            "tenant_id": uuid4(),
            "tenant_slug": "atlas-manufacturing",
            "query": "Use the enterprise system to create a ticket for MACHINE-42.",
            "tool_read_only": False,
            "may_require_write": True,
        }
    )
    assert result["requires_approval"] is True
    assert result["pending_action"]["tool_name"] == "create_maintenance_ticket"
    assert result["pending_action"]["arguments"]["asset_code"] == "MACHINE-42"


@pytest.mark.asyncio
async def test_read_only_mcp_never_requires_approval(monkeypatch):
    class FakeTool:
        def __init__(self, name: str):
            self.name = name
            self.description = name
            self.input_schema = {"type": "object", "properties": {}}

    class FakeTools:
        tools = [FakeTool("get_asset_status"), FakeTool("create_maintenance_ticket")]

    class FakeBound:
        async def ainvoke(self, messages):
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_asset_status",
                        "args": {"asset_id": "MACHINE-42"},
                        "id": "call_1",
                    }
                ],
            )

    class FakeModel:
        def bind_tools(self, schemas, **kwargs):
            assert all(s["function"]["name"] != "create_maintenance_ticket" for s in schemas)
            return FakeBound()

        async def ainvoke(self, messages):
            return AIMessage(content="MACHINE-42 is in warning state.")

    class FakeMCPResult:
        structured_content = {
            "asset_id": "MACHINE-42",
            "status": "warning",
            "tenant_slug": "atlas-manufacturing",
        }

    async def fake_call(name, args, tenant_slug=None):
        assert name == "get_asset_status"
        assert tenant_slug == "atlas-manufacturing"
        return FakeMCPResult()

    async def fake_list_tools():
        return FakeTools()

    monkeypatch.setattr(
        "app.agents.mcp_tool_node.list_maintenance_tools",
        fake_list_tools,
    )
    monkeypatch.setattr("app.agents.mcp_tool_node.get_chat_model", lambda: FakeModel())
    monkeypatch.setattr("app.agents.mcp_tool_node.call_maintenance_tool", fake_call)

    result = await mcp_tool_node(
        {
            "tenant_id": uuid4(),
            "tenant_slug": "atlas-manufacturing",
            "query": "What is the current operational status of MACHINE-42?",
            "tool_read_only": True,
            "may_require_write": False,
        }
    )
    assert result.get("requires_approval") is not True
    assert "warning" in result["tool_answer"].lower()


@pytest.mark.asyncio
async def test_synthesis_uses_clean_evidence_not_tool_history(monkeypatch):
    captured: dict = {}

    class FakeStructured:
        async def ainvoke(self, messages):
            captured["messages"] = messages
            from app.agents.synthesis_node import SynthesisOutput

            return SynthesisOutput(answer="Combined grounded answer.")

    class FakeModel:
        def with_structured_output(self, schema):
            return FakeStructured()

    monkeypatch.setattr("app.agents.synthesis_node.get_chat_model", lambda: FakeModel())

    result = await synthesis_node(
        {
            "query": "composite question",
            "tenant_slug": "atlas-manufacturing",
            "planned_routes": ["knowledge", "sql", "tool"],
            "rag_answer": "E-100 means lubrication pressure below threshold.",
            "sql_answer": "Two maintenance records.",
            "tool_answer": "Status warning.",
        }
    )
    assert result["synthesis_answer"] == "Combined grounded answer."
    human = captured["messages"][1][1]
    assert "Knowledge / RAG evidence" in human
    assert "SQL evidence" in human
    assert "MCP live tool evidence" in human
    assert "tool_calls" not in human


@pytest.mark.asyncio
async def test_composite_hitl_write_gate_after_synthesis(monkeypatch):
    from app.agents import graph as graph_module

    async def fake_planner(state):
        return {
            "route": "knowledge",
            "planned_routes": ["knowledge", "sql", "tool"],
            "requires_synthesis": True,
            "may_require_write": True,
            "tool_read_only": True,
            "execution_details": {
                "graph_path": ["planner"],
                "selected_capabilities": ["knowledge", "sql", "tool"],
            },
        }

    async def fake_rag(state):
        return {"rag_answer": "Isolate and inspect.", "execution_details": {"graph_path": ["rag"]}}

    async def fake_sql(state):
        return {"sql_answer": "Two prior records.", "execution_details": {"graph_path": ["sql"]}}

    async def fake_tool(state):
        assert state.get("tool_read_only") is True
        return {"tool_answer": "Status warning.", "execution_details": {"graph_path": ["tool"]}}

    async def fake_synthesis(state):
        return {
            "synthesis_answer": "Intervention warranted.",
            "execution_details": {"graph_path": ["synthesize"]},
        }

    async def fake_write_gate(state):
        return {
            "requires_approval": True,
            "pending_action": {
                "tool_name": "create_maintenance_ticket",
                "arguments": {
                    "asset_code": "MACHINE-42",
                    "issue": "Hydraulic pressure loss",
                    "priority": "high",
                },
            },
            "tool_answer": "This action requires human approval before execution.",
            "execution_details": {"graph_path": ["write_gate"]},
        }

    monkeypatch.setattr(graph_module, "planner_node", fake_planner)
    monkeypatch.setattr(graph_module, "rag_node", fake_rag)
    monkeypatch.setattr(graph_module, "sql_node", fake_sql)
    monkeypatch.setattr(graph_module, "mcp_tool_node", fake_tool)
    monkeypatch.setattr(graph_module, "synthesis_node", fake_synthesis)
    monkeypatch.setattr(graph_module, "write_gate_node", fake_write_gate)

    compiled = graph_module.build_agent_graph().compile(checkpointer=InMemorySaver())
    result = await compiled.ainvoke(
        {
            "tenant_id": uuid4(),
            "tenant_slug": "atlas-manufacturing",
            "query": "Create a ticket if needed after reviewing MACHINE-42.",
            "retrieval_mode": "standard",
        },
        config={"configurable": {"thread_id": str(uuid4())}},
    )
    assert result.get("__interrupt__")
    assert result["pending_action"]["tool_name"] == "create_maintenance_ticket"
    assert result.get("synthesis_answer")


@pytest.mark.asyncio
async def test_evaluator_preflight_fails_before_ai(monkeypatch):
    from evals.agent import run_agent_evaluation as eval_mod

    async def fake_scalars_empty(*args, **kwargs):
        class Empty:
            def all(self):
                return []

        return Empty()

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def scalars(self, *args, **kwargs):
            return await fake_scalars_empty()

    monkeypatch.setattr(eval_mod, "SessionLocal", lambda: FakeSession())

    with pytest.raises(RuntimeError, match="not seeded"):
        await eval_mod.preflight_required_tenants(
            [{"tenant_slug": "atlas-manufacturing", "expected_route": "knowledge"}]
        )
