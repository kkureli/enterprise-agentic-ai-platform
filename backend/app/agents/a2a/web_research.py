"""Lightweight public-web research helpers (no extra search API dependency)."""

from __future__ import annotations

import logging
import re
from urllib.parse import quote

import httpx

from app.agents.a2a.schemas import EvidenceItem

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html(text: str) -> str:
    cleaned = _TAG_RE.sub(" ", text)
    return _WS_RE.sub(" ", cleaned).strip()


async def fetch_wikipedia_summary(title: str) -> EvidenceItem | None:
    """Fetch a public Wikipedia REST summary for entity-grounded research."""

    if not title.strip():
        return None

    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title.strip())}"
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "enterprise-agentic-ai-platform/1.0",
                },
            )
        if response.status_code != 200:
            return None
        payload = response.json()
        extract = (payload.get("extract") or "").strip()
        if not extract:
            return None
        page_url = (
            (payload.get("content_urls") or {}).get("desktop", {}) or {}
        ).get("page") or url
        return EvidenceItem(
            summary=extract[:1200],
            source_type="web",
            source_url=page_url,
            source_title=payload.get("title") or title,
            confidence=0.75,
        )
    except Exception:
        logger.exception("Wikipedia summary fetch failed for title=%s", title)
        return None


async def fetch_url_text_snippet(url: str, *, max_chars: int = 800) -> EvidenceItem | None:
    """Fetch a short text snippet from a public URL."""

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "enterprise-agentic-ai-platform/1.0"},
            )
        if response.status_code != 200:
            return None
        text = _strip_html(response.text)
        if len(text) < 40:
            return None
        return EvidenceItem(
            summary=text[:max_chars],
            source_type="web",
            source_url=str(response.url),
            source_title=str(response.url),
            confidence=0.55,
        )
    except Exception:
        logger.exception("URL snippet fetch failed for url=%s", url)
        return None


async def collect_public_evidence(
    *,
    company_name: str,
    domain: str | None,
    extra_queries: list[str] | None = None,
) -> list[EvidenceItem]:
    """Collect a small set of public evidence items for a resolved company."""

    evidence: list[EvidenceItem] = []
    wiki = await fetch_wikipedia_summary(company_name)
    if wiki is not None:
        evidence.append(wiki)

    if domain:
        homepage = domain if domain.startswith("http") else f"https://{domain}"
        snippet = await fetch_url_text_snippet(homepage)
        if snippet is not None:
            evidence.append(snippet)

    # Extra queries currently reinforce Wikipedia title attempts only (no paid SERP).
    for query in (extra_queries or [])[:2]:
        # Avoid duplicate Wikipedia hits for near-identical titles.
        if _normalize_title(query) == _normalize_title(company_name):
            continue
        item = await fetch_wikipedia_summary(query)
        if item is not None:
            evidence.append(item)

    return evidence


def _normalize_title(value: str) -> str:
    return " ".join(value.strip().lower().split())
