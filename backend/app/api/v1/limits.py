"""HTTP helpers for rate-limit responses."""

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.services.client_identity import LimitDecision


def raise_limit_error(decision: LimitDecision) -> None:
    headers = {}
    if decision.retry_after_seconds is not None:
        headers["Retry-After"] = str(decision.retry_after_seconds)

    raise HTTPException(
        status_code=decision.status_code,
        detail=decision.reason or "Request limit exceeded.",
        headers=headers or None,
    )


def limit_error_response(decision: LimitDecision) -> JSONResponse:
    headers = {}
    if decision.retry_after_seconds is not None:
        headers["Retry-After"] = str(decision.retry_after_seconds)

    return JSONResponse(
        status_code=decision.status_code,
        content={"detail": decision.reason or "Request limit exceeded."},
        headers=headers or None,
    )
