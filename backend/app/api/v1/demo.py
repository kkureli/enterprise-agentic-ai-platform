from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.demo_tenants import DEMO_TENANTS
from app.core.readiness import check_postgres, check_qdrant, check_redis
from app.db.session import get_db
from app.models.tenant import Tenant
from app.schemas.demo import DemoTenantRead
from app.services.evaluation_summary import (
    DemoEvaluationsResponse,
    DemoUsageResponse,
    SystemComponentStatus,
    SystemStatusResponse,
    load_evaluation_summary,
)
from app.services.rate_limit_service import demo_usage_status

router = APIRouter(
    prefix="/demo",
    tags=["Demo"],
)


@router.get(
    "/tenants",
    response_model=list[DemoTenantRead],
)
async def list_demo_tenants(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DemoTenantRead]:
    """Return only the known public playground demo tenants."""

    result = await db.execute(
        select(Tenant).where(
            Tenant.name.in_([spec.name for spec in DEMO_TENANTS]),
        )
    )
    tenants_by_name = {tenant.name: tenant for tenant in result.scalars().all()}

    demo_tenants: list[DemoTenantRead] = []

    for spec in DEMO_TENANTS:
        tenant = tenants_by_name.get(spec.name)

        if tenant is None:
            continue

        demo_tenants.append(
            DemoTenantRead(
                id=tenant.id,
                name=spec.name,
                description=spec.description,
                short_label=spec.short_label,
            )
        )

    return demo_tenants


@router.get(
    "/evaluations",
    response_model=DemoEvaluationsResponse,
)
async def get_demo_evaluations() -> DemoEvaluationsResponse:
    return load_evaluation_summary()


@router.get(
    "/usage",
    response_model=DemoUsageResponse,
)
async def get_demo_usage() -> DemoUsageResponse:
    return DemoUsageResponse(status=await demo_usage_status())


@router.get(
    "/status",
    response_model=SystemStatusResponse,
)
async def get_system_status() -> SystemStatusResponse:
    postgres = await check_postgres()
    qdrant = await check_qdrant()
    redis = await check_redis() if settings.redis_enabled else False

    def label(ok: bool, *, required: bool = True) -> str:
        if ok:
            return "Healthy"
        if required:
            return "Unavailable"
        return "Degraded"

    components = [
        SystemComponentStatus(
            name="Backend",
            status="Healthy",
            role="FastAPI application process",
        ),
        SystemComponentStatus(
            name="PostgreSQL",
            status=label(postgres),
            role="Application data + LangGraph checkpoints",
        ),
        SystemComponentStatus(
            name="Qdrant",
            status=label(qdrant),
            role="Tenant-scoped RAG vectors",
        ),
        SystemComponentStatus(
            name="Redis",
            status=label(redis, required=False) if settings.redis_enabled else "Degraded",
            role="RAG cache + rate limiting",
        ),
        SystemComponentStatus(
            name="AI service",
            status="Available"
            if settings.azure_openai_endpoint and settings.azure_openai_deployment
            else "Unknown",
            role="Azure OpenAI / Foundry (config present; not probed with an LLM call)",
        ),
    ]

    if not postgres or not qdrant:
        overall = "Unavailable"
    elif settings.redis_enabled and not redis:
        overall = "Degraded"
    else:
        overall = "Healthy"

    return SystemStatusResponse(overall=overall, components=components)
