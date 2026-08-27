# A2A Agent Layer (Sprint 3)

Standalone agent-to-agent research + risk assessment for commercial entities.

## Components

| Module | Role |
|--------|------|
| `schemas.py` | Shared structured contracts |
| `entity_resolution.py` | Tenant-safe company matching |
| `web_research.py` | Public Wikipedia / domain evidence |
| `company_intelligence_agent.py` | External research agent |
| `risk_agent.py` | Risk assessment + A2A follow-up hop |
| `company_extract.py` | Pull company name from free text |
| `pipeline.py` | End-to-end `run_a2a_external_risk_pipeline` |

## Flow

```text
Question
  → extract company (Spotify / Microsoft / …)
  → Company Intelligence (entity resolve + public evidence)
  → Risk Agent (SQL + RAG + external evidence)
       ↘ if evidence thin
         A2A follow-up task → Company Intelligence
       ↗ additional evidence
  → final RiskAssessmentResult
```

## Usage (Python)

```python
from app.agents.a2a import run_a2a_external_risk_pipeline

result = await run_a2a_external_risk_pipeline(
    tenant_id=northstar_tenant_id,
    question="Assess Microsoft external and internal risks.",
    response_language="en",
)
print(result.answer)
print(result.state_updates())  # for AgentState
```

## LangGraph

Planner capability `external_risk_assessment` maps to graph node `a2a_risk`
(`a2a_risk_node` → `run_a2a_external_risk_pipeline`).

On the **single-route** path the node also loads RAG context (contracts /
account reviews) so Risk Agent sees SQL + RAG + public web evidence.
When `knowledge` is already planned (composite), RAG is left to the parallel
`rag` node / synthesis path.

## Medium / high risk → HITL → GitHub

If `risk_level` is `medium` or `high`, `a2a_risk_node` sets `pending_action`
for `create_github_issue` and interrupts for human approval. Approve runs MCP
(real GitHub Issue) + SQL audit/link; reject performs no external write.
`low` remains informational only.
