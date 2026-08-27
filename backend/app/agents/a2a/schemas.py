"""Structured contracts for A2A Company Intelligence and Risk agents.

Runtime agents are added in later Sprint 3 tasks; these schemas are the shared
evidence / result shapes written into AgentState.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RiskLevel = Literal["low", "medium", "high"]
A2AAgentName = Literal["company_intelligence", "risk"]


class EvidenceItem(BaseModel):
    """One piece of grounded evidence with optional source metadata."""

    summary: str = Field(min_length=1)
    source_type: Literal["web", "sql", "rag", "a2a", "other"] = "web"
    source_url: str | None = None
    source_title: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class EntityResolution(BaseModel):
    """Resolved company identity used to avoid wrong-entity research."""

    internal_customer_id: str | None = None
    company_name: str | None = None
    official_name: str | None = None
    domain: str | None = None
    matched_aliases: list[str] = Field(default_factory=list)
    resolution_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    unresolved: bool = False


class CompanyIntelligenceResult(BaseModel):
    """Structured output from the Company Intelligence Agent."""

    company_query: str = Field(min_length=1)
    entity: EntityResolution
    search_queries: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    evidence_sufficient: bool = True
    notes: str | None = None


class A2AFollowUpTask(BaseModel):
    """Agent-to-agent research delegation request."""

    from_agent: A2AAgentName
    to_agent: A2AAgentName
    task: str = Field(min_length=1)
    company_query: str | None = None
    reason: str | None = None


class RiskAssessmentResult(BaseModel):
    """Structured output from the Risk Agent."""

    risk_level: RiskLevel
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceItem] = Field(default_factory=list)
    needs_more_evidence: bool = False
    follow_up_task: A2AFollowUpTask | None = None
