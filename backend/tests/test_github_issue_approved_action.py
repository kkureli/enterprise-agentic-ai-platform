"""Tests for HITL-approved GitHub issue creation via MCP."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.approved_action_service import (
    APPROVED_WRITE_ACTIONS,
    execute_approved_action,
)


@pytest.mark.asyncio
async def test_execute_create_github_issue_calls_mcp_and_audits(monkeypatch) -> None:
    tenant_id = uuid4()
    created = {"link": False, "escalation": False}
    escalation_id = uuid4()

    async def fake_find(*, tenant_id, dedupe_key):
        return None

    async def fake_escalation(**kwargs):
        created["escalation"] = True
        return SimpleNamespace(id=escalation_id)

    async def fake_mcp(name, arguments, *, tenant_slug=None):
        assert name == "create_github_issue"
        assert arguments["title"].startswith("[Risk]")
        assert arguments["dedupe_key"] == "northstar:microsoft:high"
        assert tenant_slug == "northstar-commercial"
        return SimpleNamespace(
            structured_content={
                "number": 42,
                "id": "999001",
                "title": arguments["title"],
                "html_url": "https://github.com/kkureli/enterprise-agentic-ai-platform/issues/42",
                "state": "open",
                "repository": "kkureli/enterprise-agentic-ai-platform",
                "tenant_slug": tenant_slug,
                "dedupe_key": arguments["dedupe_key"],
            }
        )

    async def fake_create_link(**kwargs):
        created["link"] = True
        assert kwargs["provider"] == "github"
        assert kwargs["external_id"] == "999001"
        assert kwargs["dedupe_key"] == "northstar:microsoft:high"
        assert kwargs["risk_escalation_id"] == escalation_id
        return SimpleNamespace(
            provider="github",
            external_id="999001",
            external_url=kwargs["external_url"],
            status="open",
            dedupe_key=kwargs["dedupe_key"],
            company_query=kwargs.get("company_query"),
            internal_ticket_id=None,
            risk_escalation_id=escalation_id,
        )

    monkeypatch.setattr(
        "app.services.approved_action_service.find_external_action_link",
        fake_find,
    )
    monkeypatch.setattr(
        "app.services.approved_action_service.create_risk_escalation",
        fake_escalation,
    )
    monkeypatch.setattr(
        "app.services.approved_action_service.call_maintenance_tool",
        fake_mcp,
    )
    monkeypatch.setattr(
        "app.services.approved_action_service.create_external_action_link",
        fake_create_link,
    )

    result = await execute_approved_action(
        tenant_id,
        {
            "tool_name": "create_github_issue",
            "arguments": {
                "title": "[Risk] Microsoft high",
                "body": "Escalate Microsoft account risk.",
                "tenant_slug": "northstar-commercial",
                "dedupe_key": "northstar:microsoft:high",
                "company_query": "Microsoft",
                "risk_level": "high",
                "labels": ["risk", "agentic"],
            },
        },
    )
    assert result["deduplicated"] is False
    assert result["external_url"].endswith("/issues/42")
    assert result["issue_number"] == 42
    assert result["risk_escalation_id"] == str(escalation_id)
    assert created["link"] is True
    assert created["escalation"] is True


@pytest.mark.asyncio
async def test_execute_create_github_issue_dedupes(monkeypatch) -> None:
    existing = SimpleNamespace(
        provider="github",
        external_id="111",
        external_url="https://github.com/kkureli/enterprise-agentic-ai-platform/issues/11",
        status="open",
        dedupe_key="northstar:spotify:high",
        company_query="Spotify",
        internal_ticket_id=None,
        risk_escalation_id=None,
    )

    async def fake_find(*, tenant_id, dedupe_key):
        return existing

    async def fail_mcp(*args, **kwargs):
        raise AssertionError("MCP must not be called when deduped")

    monkeypatch.setattr(
        "app.services.approved_action_service.find_external_action_link",
        fake_find,
    )
    monkeypatch.setattr(
        "app.services.approved_action_service.call_maintenance_tool",
        fail_mcp,
    )

    result = await execute_approved_action(
        uuid4(),
        {
            "tool_name": "create_github_issue",
            "arguments": {
                "title": "[Risk] Spotify",
                "body": "body",
                "tenant_slug": "northstar-commercial",
                "dedupe_key": "northstar:spotify:high",
            },
        },
    )
    assert result["deduplicated"] is True
    assert result["external_id"] == "111"


def test_create_github_issue_is_allowlisted() -> None:
    assert "create_github_issue" in APPROVED_WRITE_ACTIONS
