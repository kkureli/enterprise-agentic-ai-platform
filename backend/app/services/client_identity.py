import hashlib
import logging
from dataclasses import dataclass

from fastapi import Request

logger = logging.getLogger(__name__)


def client_ip_from_request(request: Request) -> str:
    """Resolve an effective client IP for Azure Container Apps / reverse proxies.

    Prefer the left-most X-Forwarded-For hop set by the platform ingress, then
    fall back to the immediate peer address. The raw IP is hashed before Redis
    storage by callers.
    """

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


def hash_client_id(client_ip: str) -> str:
    return hashlib.sha256(client_ip.encode("utf-8")).hexdigest()[:32]


@dataclass
class LimitDecision:
    allowed: bool
    retry_after_seconds: int | None = None
    reason: str | None = None
    status_code: int = 429
