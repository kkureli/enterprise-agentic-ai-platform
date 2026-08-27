"""Extract a company identity hint from a free-form user question."""

from __future__ import annotations

import re

# Canonical demo portfolio names (Northstar Commercial). Longest match wins.
_KNOWN_COMPANIES: tuple[str, ...] = (
    "Microsoft",
    "Siemens",
    "Shopify",
    "Spotify",
    "Adobe",
)


def extract_company_query(question: str) -> str | None:
    """Return the best-known company mention in the question, if any."""

    if not question or not question.strip():
        return None

    text = question.strip()
    lowered = text.lower()
    hits: list[tuple[int, str]] = []
    for name in _KNOWN_COMPANIES:
        pattern = re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            hits.append((match.start(), name))
        elif name.lower() in lowered:
            hits.append((lowered.index(name.lower()), name))

    if not hits:
        return None

    hits.sort(key=lambda item: item[0])
    return hits[0][1]
