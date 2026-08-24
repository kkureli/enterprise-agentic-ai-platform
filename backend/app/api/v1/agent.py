from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import agent_graph
from app.db.session import get_db
from app.models.tenant import Tenant
from app.schemas.agent import (
    AgentApprovalRequest,
    AgentRequest,
    AgentResponse,
)

router = APIRouter(
    prefix="/tenants/{tenant_id}/agent",
    tags=["Agent"],
)


@router.post(
    "",
    response_model=AgentResponse,
)
async def run_agent(
    tenant_id: UUID,
    payload: AgentRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentResponse:
    tenant = await db.get(
        Tenant,
        tenant_id,
    )

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    thread_id = str(uuid4())

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    try:
        result = await agent_graph.ainvoke(
            {
                "tenant_id": tenant_id,
                "query": payload.question,
                "retrieval_mode": payload.retrieval_mode,
            },
            config=config,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent execution failed.",
        ) from exc

    interrupts = result.get("__interrupt__")

    if interrupts:
        return AgentResponse(
            thread_id=thread_id,
            status="approval_required",
            route=result["route"],
            answer=result["tool_answer"],
            pending_action=result["pending_action"],
        )

    return AgentResponse(
        thread_id=thread_id,
        status="completed",
        route=result["route"],
        answer=result["final_answer"],
    )


@router.post(
    "/{thread_id}/approval",
    response_model=AgentResponse,
)
async def approve_agent_action(
    tenant_id: UUID,
    thread_id: str,
    payload: AgentApprovalRequest,
) -> AgentResponse:
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    snapshot = await agent_graph.aget_state(
        config,
    )

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

    return AgentResponse(
        thread_id=thread_id,
        status="completed",
        route=result["route"],
        answer=result["final_answer"],
    )
