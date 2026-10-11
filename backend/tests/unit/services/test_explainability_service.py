import pytest

from services.explainability.explainability_service import (
    ExplanationGenerationError,
    ExplainabilityService,
)
from services.explainability.voice_provider import NullVoiceProvider


class FakeExplanationProvider:
    def __init__(self):
        self.last_mode = None
        self.last_language = None
    
    async def generate(self, breakdown, mode, language):
        self.last_mode = mode
        self.last_language = language
        return "A structured explanation"


class FailingExplanationProvider:
    async def generate(self, breakdown, mode, language):
        raise ValueError("provider failed")


@pytest.mark.asyncio
async def test_explain_delegates_without_gemini():
    provider = FakeExplanationProvider()
    service = ExplainabilityService(provider)
    assert await service.explain(object(), "expert", "English") == "A structured explanation"
    assert provider.last_mode == "expert"
    assert provider.last_language == "English"


@pytest.mark.asyncio
async def test_explain_forwards_mode_and_language():
    provider = FakeExplanationProvider()
    service = ExplainabilityService(provider)
    
    # Test with custom mode and language
    await service.explain(object(), "farmer", "Swahili")
    assert provider.last_mode == "farmer"
    assert provider.last_language == "Swahili"


@pytest.mark.asyncio
async def test_explain_wraps_provider_errors():
    service = ExplainabilityService(FailingExplanationProvider())
    with pytest.raises(ExplanationGenerationError) as error:
        await service.explain(object(), "expert", "English")
    assert isinstance(error.value.__cause__, ValueError)


@pytest.mark.asyncio
async def test_null_voice_provider_is_loud():
    with pytest.raises(NotImplementedError, match="Voice narration not yet configured"):
        await NullVoiceProvider().narrate("hello")


@pytest.mark.asyncio
async def test_service_uses_null_voice_provider_by_default():
    service = ExplainabilityService(FakeExplanationProvider())
    with pytest.raises(NotImplementedError, match="Voice narration not yet configured"):
        await service.narrate("hello")


@pytest.mark.asyncio
async def test_explain_requires_mode_and_language():
    """Test that explain() raises TypeError when mode/language are not provided."""
    provider = FakeExplanationProvider()
    service = ExplainabilityService(provider)
    
    # This should raise TypeError because mode and language are required
    with pytest.raises(TypeError) as error:
        await service.explain(object())
    
    # Verify the error message indicates missing required arguments
    assert "missing" in str(error.value).lower() or "required" in str(error.value).lower()
