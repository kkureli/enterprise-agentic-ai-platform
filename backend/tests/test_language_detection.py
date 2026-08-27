from app.services.language_detection import (
    detect_response_language,
    format_response_language_instruction,
)


def test_format_response_language_instruction() -> None:
    assert format_response_language_instruction("tr") == "Response language: Turkish (tr)."
    assert format_response_language_instruction("en") == "Response language: English (en)."
    assert format_response_language_instruction(None) == "Response language: English (en)."


def test_detects_turkish_with_special_chars() -> None:
    assert detect_response_language("Spotify'ın cirosu nedir?") == "tr"


def test_detects_turkish_with_cue_words() -> None:
    assert detect_response_language("Bu musteri icin gelir nedir") == "tr"


def test_defaults_english_for_english_question() -> None:
    assert detect_response_language("What is Spotify revenue?") == "en"


def test_defaults_english_when_uncertain() -> None:
    assert detect_response_language("Spotify") == "en"
    assert detect_response_language("") == "en"
