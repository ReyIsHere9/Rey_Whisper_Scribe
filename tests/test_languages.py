from app.core.models import JobConfig
from app.core.transcribe import AUTO_LANGUAGES


def test_mixed_language_uses_auto_detection():
    assert "mixed" in AUTO_LANGUAGES
    assert JobConfig(language="mixed").language == "mixed"


def test_default_speakers_is_auto():
    assert JobConfig().expected_speakers == 0
