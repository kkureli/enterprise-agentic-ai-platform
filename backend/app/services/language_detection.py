from __future__ import annotations

import re

from app.agents.state import ResponseLanguage

_TURKISH_CHARS = set("çğıöşüÇĞİÖŞÜ")

# High-signal Turkish function words / question words (ASCII-safe forms included).
_TURKISH_WORDS = {
    "ve",
    "ile",
    "bir",
    "bu",
    "şu",
    "ne",
    "nedir",
    "nasil",
    "nasıl",
    "icin",
    "için",
    "mi",
    "mı",
    "mu",
    "mü",
    "var",
    "yok",
    "olan",
    "olarak",
    "hakkinda",
    "hakkında",
    "goster",
    "göster",
    "listele",
    "sorgula",
    "ara",
    "bul",
    "acikla",
    "açıkla",
    "hata",
    "kodu",
    "anlama",
    "anlami",
    "anlamı",
    "geliyor",
    "demek",
    "kac",
    "kaç",
    "guncel",
    "güncel",
    "durumu",
    "durum",
    "bakim",
    "bakım",
    "kaydi",
    "kaydı",
    "olustur",
    "oluştur",
    "gonder",
    "gönder",
    "mudur",
    "müdür",
    "mudurune",
    "müdürüne",
    "eposta",
    "operasyonel",
}

_WORD_RE = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşü]+", re.UNICODE)

# Explicit response-language overrides. Last match wins when both appear.
_EXPLICIT_LANGUAGE_PATTERNS: list[tuple[re.Pattern[str], ResponseLanguage]] = [
    (
        re.compile(
            r"(?:"
            r"t[uü]rk(?:çe|ce)\s+cevap\s+ver(?:ir\s+misin)?"
            r"|cevap(?:ı|i)?\s+t[uü]rk(?:çe|ce)\s+olsun"
            r"|t[uü]rk(?:çe|ce)\s+yan[ıi]t\s+ver"
            r"|yan[ıi]t[ıi]\s+t[uü]rk(?:çe|ce)\s+olsun"
            r"|please\s+answer\s+in\s+turkish"
            r"|answer\s+in\s+turkish"
            r"|respond\s+in\s+turkish"
            r"|in\s+turkish\s+please"
            r"|reply\s+in\s+turkish"
            r")",
            re.IGNORECASE,
        ),
        "tr",
    ),
    (
        re.compile(
            r"(?:"
            r"ingilizce\s+cevap\s+ver(?:ir\s+misin)?"
            r"|cevap(?:ı|i)?\s+ingilizce\s+olsun"
            r"|ingilizce\s+yan[ıi]t\s+ver"
            r"|please\s+answer\s+in\s+english"
            r"|answer\s+in\s+english"
            r"|respond\s+in\s+english"
            r"|in\s+english\s+please"
            r"|reply\s+in\s+english"
            r")",
            re.IGNORECASE,
        ),
        "en",
    ),
]


def detect_explicit_response_language(text: str) -> ResponseLanguage | None:
    """Return an explicit TR/EN preference embedded in the query, if any.

    When multiple preferences appear, the last match in the text wins.
    """
    if not text or not text.strip():
        return None

    last_match: tuple[int, ResponseLanguage] | None = None
    for pattern, language in _EXPLICIT_LANGUAGE_PATTERNS:
        for match in pattern.finditer(text):
            end = match.end()
            if last_match is None or end >= last_match[0]:
                last_match = (end, language)

    return None if last_match is None else last_match[1]


def detect_question_language(text: str) -> ResponseLanguage:
    """Detect the language of the question itself (ignores explicit overrides)."""
    if not text or not text.strip():
        return "en"

    has_turkish_char = any(ch in _TURKISH_CHARS for ch in text)
    words = {match.group(0).lower() for match in _WORD_RE.finditer(text)}
    turkish_hits = len(words & _TURKISH_WORDS)

    if has_turkish_char or turkish_hits >= 2:
        return "tr"

    return "en"


def detect_response_language(text: str) -> ResponseLanguage:
    """Resolve response language for agent answers.

    Priority:
    1. Explicit preference in the query ("Türkçe cevap ver", "answer in English")
    2. Question-language heuristic
    3. Default English
    """
    explicit = detect_explicit_response_language(text)
    if explicit is not None:
        return explicit
    return detect_question_language(text)


def format_response_language_instruction(language: str | None) -> str:
    if language == "tr":
        return "Response language: Turkish (tr)."
    return "Response language: English (en)."
