"""Build HITL-gated GitHub escalation payloads for elevated A2A risk."""

from __future__ import annotations

from app.agents.a2a.schemas import RiskAssessmentResult, RiskLevel

# Low stays informational; medium/high require human approval before GitHub write.
ESCALATION_RISK_LEVELS: frozenset[RiskLevel] = frozenset({"medium", "high"})


def should_request_github_escalation(risk_level: str | None) -> bool:
    return risk_level in ESCALATION_RISK_LEVELS


def github_escalation_dedupe_key(
    *,
    tenant_slug: str,
    company_query: str | None,
    risk_level: str,
) -> str:
    company = (company_query or "unknown").strip().lower() or "unknown"
    slug = (tenant_slug or "unknown").strip().lower() or "unknown"
    level = (risk_level or "unknown").strip().lower() or "unknown"
    return f"{slug}:{company}:external_risk:{level}"


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
    level = risk.risk_level
    level_label = level.upper()
    title = f"[Risk:{level_label}] {company} — external risk escalation"
    reasons = "\n".join(f"- {item}" for item in risk.reasons) or "- (none)"
    actions = (
        "\n".join(f"- {item}" for item in risk.recommended_actions) or "- (none)"
    )
    body = (
        f"## A2A {level} risk escalation\n\n"
        f"**Company:** {company}\n"
        f"**Tenant:** {tenant_slug}\n"
        f"**Risk level:** {level}\n"
        f"**Confidence:** {risk.confidence:.2f}\n\n"
        f"### Reasons\n{reasons}\n\n"
        f"### Recommended actions\n{actions}\n\n"
        f"### Assessment\n{assessment_answer.strip()}\n"
    )
    dedupe_key = github_escalation_dedupe_key(
        tenant_slug=tenant_slug,
        company_query=company_query,
        risk_level=level,
    )
    label = "high-risk" if level == "high" else "medium-risk"
    if response_language == "tr":
        approval_message = (
            f"{'Yüksek' if level == 'high' else 'Orta'} risk tespit edildi. "
            "GitHub Issue açmak için onay gerekli."
        )
    else:
        approval_message = (
            f"{level_label} risk detected. "
            "Approval is required to open a GitHub Issue."
        )
    pending_action = {
        "tool_name": "create_github_issue",
        "arguments": {
            "title": title[:240],
            "body": body,
            "tenant_slug": tenant_slug,
            "dedupe_key": dedupe_key,
            "company_query": company_query,
            "risk_level": level,
            "labels": ["agentic-risk", label],
        },
    }
    return {
        "requires_approval": True,
        "pending_action": pending_action,
        "tool_answer": approval_message,
    }
