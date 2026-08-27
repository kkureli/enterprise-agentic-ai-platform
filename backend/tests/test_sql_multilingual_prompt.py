from app.services.sql_generation_service import REPAIR_SYSTEM_PROMPT, SYSTEM_PROMPT


def test_sql_generation_prompt_maps_turkish_to_english_schema() -> None:
    assert "English or Turkish" in SYSTEM_PROMPT
    assert "Never invent Turkish table or column names" in SYSTEM_PROMPT
    assert "bakım kaydı" in SYSTEM_PROMPT
    assert "companies:" in SYSTEM_PROMPT
    assert "English or Turkish" in REPAIR_SYSTEM_PROMPT
