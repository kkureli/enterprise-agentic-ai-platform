from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.readiness import (
    check_postgres,
    check_qdrant,
    check_redis,
)
from app.db.session import close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

    await close_db()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
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
    postgres = await check_postgres()
    redis = await check_redis()
    qdrant = await check_qdrant()

    services = {
        "postgres": postgres,
        "redis": redis,
        "qdrant": qdrant,
    }

    ready = all(services.values())

    response = {
        "status": "ready" if ready else "not_ready",
        "services": services,
    }

    if not ready:
        return JSONResponse(
            status_code=503,
            content=response,
        )

    return response
