import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agents import graph as graph_module
from app.agents.checkpointer import (
    create_memory_checkpointer,
    create_postgres_checkpointer,
)
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.readiness import (
    check_postgres,
    check_qdrant,
    check_redis,
)
from app.db.session import close_db
from app.services.redis_service import close_redis, init_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    checkpoint_pool = None

    await init_redis()

    if settings.checkpoint_backend == "postgres":
        checkpointer, checkpoint_pool = await create_postgres_checkpointer(
            settings.database_url,
        )
        graph_module.checkpointer = checkpointer
        graph_module.agent_graph = graph_module.compile_agent_graph(checkpointer)
    else:
        checkpointer = create_memory_checkpointer()
        graph_module.checkpointer = checkpointer
        graph_module.agent_graph = graph_module.compile_agent_graph(checkpointer)

    try:
        yield
    finally:
        if checkpoint_pool is not None:
            await checkpoint_pool.close()

        await close_redis()
        await close_db()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Retry-After"],
)


app.include_router(
    api_router,
    prefix=settings.api_v1_prefix,
)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "environment": settings.app_env,
    }


@app.get("/ready")
async def readiness_check():
    postgres, redis, qdrant = await asyncio.gather(
        check_postgres(),
        check_redis(),
        check_qdrant(),
    )

    services = {
        "postgres": postgres,
        "redis": redis,
        "qdrant": qdrant,
    }

    # Hard dependencies: PostgreSQL and Qdrant.
    # Redis is degraded-mode (RAG cache + rate limiting fail open).
    hard_ready = postgres and qdrant
    degraded = hard_ready and settings.redis_enabled and not redis

    if not hard_ready:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "services": services,
                "degraded": False,
            },
        )

    return {
        "status": "ready",
        "services": services,
        "degraded": degraded,
    }
