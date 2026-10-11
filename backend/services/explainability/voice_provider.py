"""Voice narration contract reserved for a later implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod


class VoiceNarrationProvider(ABC):
    """Convert explanation text into provider-defined raw audio bytes."""

    @abstractmethod
    async def narrate(self, explanation_text: str, language: str = "en") -> bytes:
        """Return audio bytes for the requested language."""
        raise NotImplementedError


class NullVoiceProvider(VoiceNarrationProvider):
    """Fail loudly until a real narration provider is implemented."""

    async def narrate(self, explanation_text: str, language: str = "en") -> bytes:
        raise NotImplementedError(
            "Voice narration not yet configured - see "
            "services/explainability/voice_provider.py"
        )
