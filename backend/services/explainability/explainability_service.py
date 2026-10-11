"""Application service for provider-backed explanations."""

from __future__ import annotations

from typing import Literal

from services.scoring_service import ScoreComputationResult
from services.explainability.provider import ExplanationProvider
from services.explainability.voice_provider import (
    NullVoiceProvider,
    VoiceNarrationProvider,
)


class ExplanationGenerationError(RuntimeError):
    """Provider-independent error exposed to API callers."""


class ExplainabilityService:
    """Delegate explanation and future voice work without database access."""

    def __init__(
        self,
        provider: ExplanationProvider,
        voice_provider: VoiceNarrationProvider = NullVoiceProvider(),
    ) -> None:
        self.provider = provider
        self.voice_provider = voice_provider

    async def explain(
        self, 
        breakdown: ScoreComputationResult,
        mode: Literal["expert", "farmer"],
        language: str
    ) -> str:
        try:
            return await self.provider.generate(breakdown, mode, language)
        except Exception as exc:
            raise ExplanationGenerationError(
                "The explanation provider failed to generate an explanation"
            ) from exc

    async def narrate(self, explanation_text: str, language: str = "en") -> bytes:
        return await self.voice_provider.narrate(explanation_text, language)
