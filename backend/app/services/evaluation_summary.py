import json
from pathlib import Path

from pydantic import BaseModel, Field


class AgentEvaluationSummary(BaseModel):
    total_cases: int
    route_accuracy: float
    approval_accuracy: float
    execution_success_rate: float
    end_to_end_pass_rate: float
    required_capability_recall: float | None = None
    exact_capability_set_accuracy: float | None = None
    unnecessary_capability_rate: float | None = None
    per_capability_execution_success: float | None = None
    synthesis_required_fact_coverage: float | None = None
    tenant_correctness: float | None = None
    composite_cases: int | None = None


class RetrievalStrategyMetrics(BaseModel):
    name: str
    recall_at_k: float
    mrr: float
    ndcg_at_k: float


class RetrievalEvaluationSummary(BaseModel):
    num_queries: int
    eval_k: int
    strategies: list[RetrievalStrategyMetrics]


class DemoEvaluationsResponse(BaseModel):
    disclaimer: str
    agent: AgentEvaluationSummary
    retrieval: RetrievalEvaluationSummary


class DemoUsageResponse(BaseModel):
    status: str = Field(description="available | limited")


class SystemComponentStatus(BaseModel):
    name: str
    status: str
    role: str | None = None


class SystemStatusResponse(BaseModel):
    overall: str
    components: list[SystemComponentStatus]


_AGENT_SUMMARY_KEYS = {
    "total_cases",
    "route_accuracy",
    "approval_accuracy",
    "execution_success_rate",
    "end_to_end_pass_rate",
    "required_capability_recall",
    "exact_capability_set_accuracy",
    "unnecessary_capability_rate",
    "per_capability_execution_success",
    "synthesis_required_fact_coverage",
    "tenant_correctness",
    "composite_cases",
}


def load_evaluation_summary() -> DemoEvaluationsResponse:
    packaged = Path(__file__).resolve().parents[1] / "data" / "evaluation_summary.json"
    monorepo = Path(__file__).resolve().parents[3] / "evals" / "results"

    if packaged.exists():
        raw = json.loads(packaged.read_text(encoding="utf-8"))
    else:
        # Local fallback: assemble from live eval artifacts when present.
        agent_path = monorepo / "agent_evaluation.json"
        retrieval_path = monorepo / "retrieval_results.json"
        agent_raw = json.loads(agent_path.read_text(encoding="utf-8"))
        retrieval_raw = json.loads(retrieval_path.read_text(encoding="utf-8"))
        raw = {
            "disclaimer": (
                "Metrics are from a curated regression dataset and are not "
                "claims of universal production accuracy."
            ),
            "agent": {
                "total_cases": agent_raw["total_cases"],
                **agent_raw["metrics"],
            },
            "retrieval": {
                "num_queries": retrieval_raw["num_queries"],
                "eval_k": retrieval_raw["eval_k"],
                "strategies": {
                    name: {
                        "recall_at_k": metrics["recall@3"],
                        "mrr": metrics["mrr"],
                        "ndcg_at_k": metrics["ndcg@3"],
                    }
                    for name, metrics in retrieval_raw["strategies"].items()
                },
            },
        }

    agent_payload = {
        key: value for key, value in raw["agent"].items() if key in _AGENT_SUMMARY_KEYS
    }

    strategies_raw = raw["retrieval"]["strategies"]
    if isinstance(strategies_raw, dict):
        strategies = [
            RetrievalStrategyMetrics(name=name, **metrics)
            for name, metrics in strategies_raw.items()
        ]
    else:
        strategies = [RetrievalStrategyMetrics(**item) for item in strategies_raw]

    return DemoEvaluationsResponse(
        disclaimer=raw["disclaimer"],
        agent=AgentEvaluationSummary(**agent_payload),
        retrieval=RetrievalEvaluationSummary(
            num_queries=raw["retrieval"]["num_queries"],
            eval_k=raw["retrieval"]["eval_k"],
            strategies=strategies,
        ),
    )
