"""Helpers for building safe per-request execution traces for the playground."""

from __future__ import annotations

import time
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from app.core.config import settings
from app.schemas.execution import (
    CacheDetails,
    CostDetails,
    ExecutionDetails,
    HitlDetails,
    LlmUsageDetails,
    RetrievalChunkDetail,
    RetrievalDetails,
    SqlDetails,
    TimingDetails,
    ToolDetails,
    A2aDetails,
)


def merge_execution_details(
    left: dict[str, Any] | None,
    right: dict[str, Any] | None,
) -> dict[str, Any]:
    if not left:
        return dict(right or {})
    if not right:
        return dict(left)

    merged = {**left, **right}

    left_path = list(left.get("graph_path") or [])
    right_path = list(right.get("graph_path") or [])
    if left_path or right_path:
        merged["graph_path"] = left_path + right_path

    left_timing = dict(left.get("timing") or {})
    right_timing = dict(right.get("timing") or {})
    if left_timing or right_timing:
        merged["timing"] = {**left_timing, **right_timing}

    # Preserve multi-capability provenance: do not drop earlier sections when a
    # later node omits them (dict spread already keeps left-only keys).
    for key in ("retrieval", "sources", "sql", "tools", "hitl", "cache"):
        if key in left and key not in right:
            merged[key] = left[key]
        elif key in left and right.get(key) is None and left.get(key) is not None:
            merged[key] = left[key]

    left_caps = list(left.get("selected_capabilities") or [])
    right_caps = list(right.get("selected_capabilities") or [])
    if left_caps or right_caps:
        seen: set[str] = set()
        caps: list[str] = []
        for item in left_caps + right_caps:
            if item in seen:
                continue
            seen.add(item)
            caps.append(item)
        merged["selected_capabilities"] = caps

    # Keep planner primary route when multiple capabilities were selected.
    if len(merged.get("selected_capabilities") or []) > 1 and left.get("route"):
        merged["route"] = left["route"]

    return merged


def node_trace(node_name: str, **sections: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"graph_path": [node_name]}
    for key, value in sections.items():
        if value is not None:
            payload[key] = value
    return {"execution_details": payload}


def elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


class TokenUsageCallback(BaseCallbackHandler):
    """Aggregate token usage across all LLM calls in one agent request."""

    def __init__(self) -> None:
        self.llm_call_count = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.model: str | None = settings.azure_openai_deployment

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        self.llm_call_count += 1

        usage = _extract_usage(response)
        if usage is None:
            return

        input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
        output_tokens = usage.get("output_tokens") or usage.get("completion_tokens") or 0
        total_tokens = usage.get("total_tokens")
        if total_tokens is None:
            total_tokens = int(input_tokens) + int(output_tokens)

        self.input_tokens += int(input_tokens)
        self.output_tokens += int(output_tokens)
        self.total_tokens += int(total_tokens)

        model_name = usage.get("model_name") or usage.get("model")
        if isinstance(model_name, str) and model_name:
            self.model = model_name

    def to_details(self) -> LlmUsageDetails:
        has_tokens = self.total_tokens > 0 or self.input_tokens > 0 or self.output_tokens > 0
        return LlmUsageDetails(
            model=self.model,
            llm_call_count=self.llm_call_count,
            input_tokens=self.input_tokens if has_tokens else None,
            output_tokens=self.output_tokens if has_tokens else None,
            total_tokens=self.total_tokens if has_tokens else None,
        )


def _extract_usage(response: LLMResult) -> dict[str, Any] | None:
    if response.llm_output and isinstance(response.llm_output, dict):
        token_usage = response.llm_output.get("token_usage") or response.llm_output.get("usage")
        if isinstance(token_usage, dict):
            return token_usage

    for generations in response.generations:
        for generation in generations:
            message = getattr(generation, "message", None)
            if message is None:
                continue

            usage_metadata = getattr(message, "usage_metadata", None)
            if isinstance(usage_metadata, dict) and usage_metadata:
                return usage_metadata

            response_metadata = getattr(message, "response_metadata", None)
            if isinstance(response_metadata, dict):
                token_usage = response_metadata.get("token_usage") or response_metadata.get("usage")
                if isinstance(token_usage, dict):
                    return token_usage

    return None


def estimate_cost(usage: LlmUsageDetails) -> CostDetails | None:
    input_tokens = usage.input_tokens or 0
    output_tokens = usage.output_tokens or 0

    if input_tokens == 0 and output_tokens == 0:
        return None

    llm_cost = (input_tokens / 1_000_000) * settings.llm_input_cost_per_1m_tokens + (
        output_tokens / 1_000_000
    ) * settings.llm_output_cost_per_1m_tokens

    return CostDetails(
        estimated_llm_cost_usd=round(llm_cost, 6),
        estimated_embedding_cost_usd=None,
        estimated_total_cost_usd=round(llm_cost, 6),
        label="Estimated cost",
    )


def build_execution_details(
    raw: dict[str, Any] | None,
    *,
    route: str | None,
    usage: TokenUsageCallback,
    total_ms: float | None = None,
    observability_id: str | None = None,
) -> ExecutionDetails:
    data = dict(raw or {})
    timing_raw = dict(data.get("timing") or {})
    if total_ms is not None:
        timing_raw["total_ms"] = total_ms

    llm_usage = usage.to_details()
    cost = estimate_cost(llm_usage)

    retrieval = None
    if data.get("retrieval"):
        retrieval = RetrievalDetails.model_validate(data["retrieval"])

    sources = None
    if data.get("sources") is not None:
        sources = [RetrievalChunkDetail.model_validate(item) for item in data["sources"]]

    return ExecutionDetails(
        route=route or data.get("route"),
        selected_capabilities=list(data.get("selected_capabilities") or []),
        graph_path=list(data.get("graph_path") or []),
        retrieval=retrieval,
        sources=sources,
        sql=SqlDetails.model_validate(data["sql"]) if data.get("sql") else None,
        tools=ToolDetails.model_validate(data["tools"]) if data.get("tools") else None,
        a2a=A2aDetails.model_validate(data["a2a"]) if data.get("a2a") else None,
        hitl=HitlDetails.model_validate(data["hitl"]) if data.get("hitl") else None,
        cache=CacheDetails.model_validate(data["cache"]) if data.get("cache") else None,
        llm_usage=llm_usage,
        cost=cost,
        timing=TimingDetails.model_validate(timing_raw) if timing_raw else None,
        observability_id=observability_id,
    )


def safe_result_preview(value: Any, *, max_length: int = 500) -> str:
    text = str(value)
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
