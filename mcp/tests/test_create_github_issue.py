"""Unit tests for MCP GitHub issue helper (mocked HTTP)."""

from __future__ import annotations

import os

import httpx
import pytest

# Import after path: tests run from mcp/ or via pytest on this file.
from server import GitHubIssueResult, create_github_issue


def test_create_github_issue_posts_to_repo(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghs_test_token")
    monkeypatch.setenv("GITHUB_REPO", "kkureli/enterprise-agentic-ai-platform")

    def fake_post(url, headers=None, json=None, timeout=None):
        assert url.endswith("/repos/kkureli/enterprise-agentic-ai-platform/issues")
        assert headers["Authorization"] == "Bearer ghs_test_token"
        assert json["title"] == "Escalate Microsoft"
        assert "agent-dedupe:northstar:microsoft:high" in json["body"]
        assert json["labels"] == ["risk"]
        return httpx.Response(
            201,
            json={
                "number": 7,
                "id": 555,
                "title": "Escalate Microsoft",
                "html_url": "https://github.com/kkureli/enterprise-agentic-ai-platform/issues/7",
                "state": "open",
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    result = create_github_issue(
        title="Escalate Microsoft",
        body="High risk account.",
        tenant_slug="northstar-commercial",
        labels=["risk"],
        dedupe_key="northstar:microsoft:high",
    )
    assert isinstance(result, GitHubIssueResult)
    assert result.number == 7
    assert result.html_url.endswith("/issues/7")
    assert result.repository == "kkureli/enterprise-agentic-ai-platform"


def test_create_github_issue_requires_token(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
        create_github_issue(
            title="x",
            body="y",
            tenant_slug="northstar-commercial",
        )
