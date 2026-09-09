from app.voice.language import language_service


def test_english():
    result = language_service.detect(
        "Find me a flight to Delhi tomorrow"
    )

    assert result.primary_language == "en"
    assert result.is_code_switched is False


def test_hindi():
    result = language_service.detect(
        "Mujhe Delhi jaana hai kal"
    )

    assert result.primary_language == "hi"


def test_hinglish():
    result = language_service.detect(
        "Mujhe Delhi jaana hai tomorrow morning"
    )

    assert result.is_code_switched is True


def test_empty_text():
    result = language_service.detect("")

    assert result.primary_language == "unknown"
    assert result.is_code_switched is False