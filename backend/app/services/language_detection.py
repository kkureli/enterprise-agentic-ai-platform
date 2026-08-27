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


def detect_response_language(text: str) -> ResponseLanguage:
    """Detect TR vs EN for agent responses.

    Prefer Turkish when Turkish letters or enough Turkish cue words appear.
    Default to English when uncertain so existing EN behavior stays stable.
    """
    if not text or not text.strip():
        return "en"

    has_turkish_char = any(ch in _TURKISH_CHARS for ch in text)
    words = {match.group(0).lower() for match in _WORD_RE.finditer(text)}
    turkish_hits = len(words & _TURKISH_WORDS)

    if has_turkish_char or turkish_hits >= 2:
        return "tr"

    return "en"


def format_response_language_instruction(language: str | None) -> str:
    if language == "tr":
        return "Response language: Turkish (tr)."
    return "Response language: English (en)."
