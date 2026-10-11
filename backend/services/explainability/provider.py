"""Provider contract for structured score explanations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from services.scoring_service import ScoreComputationResult


class ExplanationProvider(ABC):
    """Generate prose from the complete structured scoring breakdown."""

    @abstractmethod
    async def generate(
        self, 
        breakdown: ScoreComputationResult,
        mode: Literal["expert", "farmer"],
        language: str
    ) -> str:
        """Return an explanation without reducing the breakdown to one number."""
        raise NotImplementedError
