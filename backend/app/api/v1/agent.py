import logging
import time
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from langfuse.langchain import CallbackHandler
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.execution_trace import (
    TokenUsageCallback,
    build_execution_details,
    merge_execution_details,
)
from app.agents.graph import agent_graph
from app.api.v1.limits import raise_limit_error
from app.core.demo_tenants import demo_tenant_slug_for_name
from app.db.session import get_db
from app.models.tenant import Tenant
from app.schemas.agent import (
    AgentApprovalRequest,
    AgentCompareRequest,
    AgentCompareResponse,
    AgentRequest,
    AgentResponse,
)
from app.services.client_identity import client_ip_from_request, hash_client_id
from app.services.language_detection import detect_response_language
from app.services.rate_limit_service import (
    check_client_rate_limit,
    check_compare_rate_limit,
    check_daily_ai_budget,
    check_global_ai_rate_limit,
    check_tenant_rate_limit,
    check_write_rate_limit,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/tenants/{tenant_id}/agent",
    tags=["Agent"],
)


def _tenant_slug_for(tenant: Tenant) -> str:
    slug = demo_tenant_slug_for_name(tenant.name)
    if slug:
        return slug
    # Non-demo tenants still require an explicit slug for MCP isolation.
    return f"tenant-{tenant.id}"


def _response_from_result(
    *,
    thread_id: str,
    result: dict,
    usage: TokenUsageCallback,
    total_ms: float,
) -> AgentResponse:
    planned = result.get("planned_routes")
    details = build_execution_details(
        result.get("execution_details"),
        route=result.get("route"),
        usage=usage,
        total_ms=total_ms,
        observability_id=thread_id,
    )
    if planned and not details.selected_capabilities:
        details.selected_capabilities = [route for route in planned if route != "unsupported"]

    interrupts = result.get("__interrupt__")

    if interrupts:
        approval_answer = result.get("tool_answer") or ""
        a2a_answer = (result.get("a2a_answer") or "").strip()
        if a2a_answer and approval_answer:
            approval_answer = f"{a2a_answer}\n\n{approval_answer}"
        elif a2a_answer:
            approval_answer = a2a_answer
        return AgentResponse(
            thread_id=thread_id,
            status="approval_required",
            route=result["route"],
            planned_routes=planned,
            requires_synthesis=result.get("requires_synthesis"),
            answer=approval_answer,
            pending_action=result["pending_action"],
            execution_details=details,
        )

    return AgentResponse(
        thread_id=thread_id,
        status="completed",
        route=result["route"],
        planned_routes=planned,
        requires_synthesis=result.get("requires_synthesis"),
        answer=result["final_answer"],
        execution_details=details,
    )


async def _enforce_ai_request_limits(
    *,
    request: Request,
    tenant_id: UUID,
    units: int = 1,
    compare: bool = False,
) -> str:
    client_hash = hash_client_id(client_ip_from_request(request))

    if compare:
        decision = await check_compare_rate_limit(client_hash)
        if not decision.allowed:
            raise_limit_error(decision)

    for checker in (
        lambda: check_client_rate_limit(client_hash, units=units),
        lambda: check_tenant_rate_limit(tenant_id, units=units),
        lambda: check_global_ai_rate_limit(units=units),
        lambda: check_daily_ai_budget(units=units),
    ):
        decision = await checker()
        if not decision.allowed:
            raise_limit_error(decision)

    return client_hash


async def _invoke_agent(
    *,
    tenant_id: UUID,
    tenant_slug: str,
    question: str,
    retrieval_mode: str,
    run_name: str,
) -> AgentResponse:
    thread_id = str(uuid4())
    langfuse_handler = CallbackHandler()
    usage_callback = TokenUsageCallback()
    config = {
        "configurable": {
            "thread_id": thread_id,
        },
        "callbacks": [
            langfuse_handler,
            usage_callback,
        ],
        "run_name": run_name,
        "metadata": {
            "thread_id": thread_id,
            "tenant_id": str(tenant_id),
            "tenant_slug": tenant_slug,
            "retrieval_mode": retrieval_mode,
        },
    }

    started = time.perf_counter()

    try:
        result = await agent_graph.ainvoke(
            {
                "tenant_id": tenant_id,
                "tenant_slug": tenant_slug,
                "query": question,
                "retrieval_mode": retrieval_mode,
                "response_language": detect_response_language(question),
            },
            config=config,
        )
    except Exception as exc:
        logger.exception(
            "Agent execution failed for tenant=%s thread_id=%s",
            tenant_id,
            thread_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent execution failed.",
        ) from exc

    total_ms = round((time.perf_counter() - started) * 1000, 2)
    return _response_from_result(
        thread_id=thread_id,
        result=result,
        usage=usage_callback,
        total_ms=total_ms,
    )


@router.post(
    "",
    response_model=AgentResponse,
)
async def run_agent(
    tenant_id: UUID,
    payload: AgentRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentResponse:
    tenant = await db.get(Tenant, tenant_id)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    await _enforce_ai_request_limits(
        request=request,
        tenant_id=tenant_id,
        units=1,
    )

    return await _invoke_agent(
        tenant_id=tenant_id,
        tenant_slug=_tenant_slug_for(tenant),
        question=payload.question,
        retrieval_mode=payload.retrieval_mode,
        run_name="enterprise-agent",
    )


@router.post(
    "/compare",
    response_model=AgentCompareResponse,
)
async def compare_agent_runs(
    tenant_id: UUID,
    payload: AgentCompareRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentCompareResponse:
    tenant = await db.get(Tenant, tenant_id)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    # Two AI executions: compare limit + double global/daily units.
    await _enforce_ai_request_limits(
        request=request,
        tenant_id=tenant_id,
        units=2,
        compare=True,
    )

    standard = await _invoke_agent(
        tenant_id=tenant_id,
        tenant_slug=_tenant_slug_for(tenant),
        question=payload.question,
        retrieval_mode="standard",
        run_name="enterprise-agent-compare-standard",
    )
    advanced = await _invoke_agent(
        tenant_id=tenant_id,
        tenant_slug=_tenant_slug_for(tenant),
        question=payload.question,
        retrieval_mode="advanced",
        run_name="enterprise-agent-compare-advanced",
    )

    return AgentCompareResponse(
        question=payload.question,
        standard=standard,
        advanced=advanced,
    )


@router.post(
    "/{thread_id}/approval",
    response_model=AgentResponse,
)
async def approve_agent_action(
    tenant_id: UUID,
    thread_id: str,
    payload: AgentApprovalRequest,
    request: Request,
) -> AgentResponse:
    langfuse_handler = CallbackHandler()
    usage_callback = TokenUsageCallback()

    config = {
        "configurable": {
            "thread_id": thread_id,
        },
        "callbacks": [
            langfuse_handler,
            usage_callback,
        ],
        "metadata": {
            "thread_id": thread_id,
            "tenant_id": str(tenant_id),
            "approval": payload.approved,
        },
        "run_name": "enterprise-agent-approval",
    }

    snapshot = await agent_graph.aget_state(config)

    if not snapshot.values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent execution not found.",
        )

    if snapshot.values.get("tenant_id") != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent execution not found.",
        )

    if "approval" not in snapshot.next:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agent execution is not waiting for approval.",
        )

    if payload.approved:
        client_hash = hash_client_id(client_ip_from_request(request))
        write_decision = await check_write_rate_limit(client_hash)
        if not write_decision.allowed:
            raise_limit_error(write_decision)

    started = time.perf_counter()

    try:
        result = await agent_graph.ainvoke(
            Command(
                resume={
                    "approved": payload.approved,
                }
            ),
            config=config,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent execution failed.",
        ) from exc

    total_ms = round((time.perf_counter() - started) * 1000, 2)

    prior_details = snapshot.values.get("execution_details")
    if prior_details and result.get("execution_details"):
        result = {
            **result,
            "execution_details": merge_execution_details(
                prior_details,
                result.get("execution_details"),
            ),
        }
    elif prior_details and not result.get("execution_details"):
        result = {
            **result,
            "execution_details": prior_details,
        }

    return _response_from_result(
        thread_id=thread_id,
        result=result,
        usage=usage_callback,
        total_ms=total_ms,
    )
