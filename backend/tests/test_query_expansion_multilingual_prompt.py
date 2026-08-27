from app.services.query_expansion_service import SYSTEM_PROMPT


def test_query_expansion_prompt_adds_english_variants_for_turkish() -> None:
    assert "Indexed documents are primarily in English" in SYSTEM_PROMPT
    assert "English alternative" in SYSTEM_PROMPT
