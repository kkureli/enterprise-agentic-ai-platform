from app.services.language_detection import (
    detect_explicit_response_language,
    detect_question_language,
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


def test_explicit_turkish_override_on_english_question() -> None:
    question = "What is Spotify revenue? Türkçe cevap ver"
    assert detect_explicit_response_language(question) == "tr"
    assert detect_question_language("What is Spotify revenue?") == "en"
    assert detect_response_language(question) == "tr"
    assert detect_response_language("What is Spotify's annual revenue? answer in Turkish") == "tr"
    assert detect_response_language("Show Microsoft account health. Respond in Turkish.") == "tr"


def test_explicit_english_override_on_turkish_question() -> None:
    question = "Spotify'ın cirosu nedir? Answer in English"
    assert detect_explicit_response_language(question) == "en"
    assert detect_response_language(question) == "en"
    assert detect_response_language("MACHINE-42 durumu nedir? İngilizce cevap ver") == "en"


def test_last_explicit_preference_wins() -> None:
    assert (
        detect_response_language(
            "What is Spotify revenue? answer in Turkish. Actually answer in English."
        )
        == "en"
    )
    assert (
        detect_response_language("What is Spotify revenue? answer in English. Türkçe cevap ver")
        == "tr"
    )
