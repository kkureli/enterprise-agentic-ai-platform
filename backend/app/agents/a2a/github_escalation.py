"""Build HITL-gated GitHub escalation payloads for high A2A risk."""

from __future__ import annotations

from app.agents.a2a.schemas import RiskAssessmentResult


def github_escalation_dedupe_key(*, tenant_slug: str, company_query: str | None) -> str:
    company = (company_query or "unknown").strip().lower() or "unknown"
    slug = (tenant_slug or "unknown").strip().lower() or "unknown"
    return f"{slug}:{company}:external_risk:high"


def build_github_escalation_pending_action(
    *,
    tenant_slug: str,
    company_query: str | None,
    risk: RiskAssessmentResult,
    assessment_answer: str,
    response_language: str = "en",
) -> dict:
    """Return pending_action + HITL flags for create_github_issue."""

    company = (company_query or "Unknown company").strip() or "Unknown company"
    title = f"[Risk:HIGH] {company} — external risk escalation"
    reasons = "\n".join(f"- {item}" for item in risk.reasons) or "- (none)"
    actions = (
        "\n".join(f"- {item}" for item in risk.recommended_actions) or "- (none)"
    )
    body = (
        f"## A2A high-risk escalation\n\n"
        f"**Company:** {company}\n"
        f"**Tenant:** {tenant_slug}\n"
        f"**Confidence:** {risk.confidence:.2f}\n\n"
        f"### Reasons\n{reasons}\n\n"
        f"### Recommended actions\n{actions}\n\n"
        f"### Assessment\n{assessment_answer.strip()}\n"
    )
    dedupe_key = github_escalation_dedupe_key(
        tenant_slug=tenant_slug,
        company_query=company_query,
    )
    pending_action = {
        "tool_name": "create_github_issue",
        "arguments": {
            "title": title[:240],
            "body": body,
            "tenant_slug": tenant_slug,
            "dedupe_key": dedupe_key,
            "company_query": company_query,
            "labels": ["agentic-risk", "high-risk"],
        },
    }
    approval_message = (
        "Yüksek risk tespit edildi. GitHub Issue açmak için onay gerekli."
        if response_language == "tr"
        else "High risk detected. Approval is required to open a GitHub Issue."
    )
    return {
        "requires_approval": True,
        "pending_action": pending_action,
        "tool_answer": approval_message,
    }
