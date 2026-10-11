import os
import re
from datetime import datetime, timezone

import pytest

from models.scoring import ScoreComponent, ScoreProfile
from services.explainability.gemini_provider import GeminiExplanationProvider
from services.scoring_service import ScoreComputationResult

pytestmark = pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY is not configured; skipping the real Gemini provider test",
)


@pytest.mark.asyncio
async def test_gemini_generates_privacy_safe_explanation():
    profile = ScoreProfile(
        farmer_id="farmer-id-that-must-not-be-prompted",
        character_score=71,
        capacity_score=None,
        final_score=71,
        decision="ELIGIBLE",
        recommended_amount=3000,
        computed_at=datetime.now(timezone.utc),
        is_current=True,
    )
    component = ScoreComponent(
        score_profile_id=profile.id,
        axis="character",
        component_name="testimony_pool",
        raw_value="3 category-level testimonies",
        contribution=71,
        weight=0.15,
    )
    breakdown = ScoreComputationResult(
        profile=profile,
        components=[component],
        axis_note="capacity axis unavailable - character only",
    )

    explanation = await GeminiExplanationProvider().generate(breakdown, "expert", "English")

    assert explanation.strip()
    assert "Amina Wanjiku" not in explanation
    assert "NATIONAL-12345" not in explanation


@pytest.mark.asyncio
async def test_gemini_farmer_mode_output_constraints():
    """Test farmer mode output avoids forbidden words and markdown."""
    profile = ScoreProfile(
        farmer_id="farmer-id-that-must-not-be-prompted",
        character_score=71,
        capacity_score=None,
        final_score=71,
        decision="ELIGIBLE",
        recommended_amount=3000,
        computed_at=datetime.now(timezone.utc),
        is_current=True,
    )
    component = ScoreComponent(
        score_profile_id=profile.id,
        axis="character",
        component_name="testimony_pool",
        raw_value="3 category-level testimonies",
        contribution=71,
        weight=0.15,
    )
    breakdown = ScoreComputationResult(
        profile=profile,
        components=[component],
        axis_note="capacity axis unavailable - character only",
    )

    explanation = await GeminiExplanationProvider().generate(breakdown, "farmer", "English")

    # Check no forbidden words
    forbidden_words = ["axis", "component", "weight", "contribution", "pool", "algorithm", "threshold", "category"]
    for word in forbidden_words:
        assert word not in explanation.lower(), f"Found forbidden word '{word}' in farmer mode output"

    # Check no markdown characters
    assert "**" not in explanation
    assert "#" not in explanation
    assert "*" not in explanation

    # Check no raw decimal numbers (scores should be described qualitatively)
    import re
    decimal_numbers = re.findall(r"\b\d+\.\d+\b", explanation)
    assert not decimal_numbers, f"Found raw decimal numbers in farmer mode: {decimal_numbers}"


@pytest.mark.asyncio
async def test_gemini_expert_mode_output_contains_expert_terms():
    """Test expert mode output contains expert terminology."""
    profile = ScoreProfile(
        farmer_id="farmer-id-that-must-not-be-prompted",
        character_score=71,
        capacity_score=None,
        final_score=71,
        decision="ELIGIBLE",
        recommended_amount=3000,
        computed_at=datetime.now(timezone.utc),
        is_current=True,
    )
    component = ScoreComponent(
        score_profile_id=profile.id,
        axis="character",
        component_name="testimony_pool",
        raw_value="3 category-level testimonies",
        contribution=71,
        weight=0.15,
    )
    breakdown = ScoreComputationResult(
        profile=profile,
        components=[component],
        axis_note="capacity axis unavailable - character only",
    )

    explanation = await GeminiExplanationProvider().generate(breakdown, "expert", "English")

    # Should contain expert terminology
    assert "category_weight" in explanation or "axis_weight" in explanation, \
        "Expert mode output should contain expert terminology"


@pytest.mark.asyncio
async def test_gemini_swahili_language_maintains_privacy():
    """Test Swahili output still passes privacy filter."""
    profile = ScoreProfile(
        farmer_id="farmer-id-that-must-not-be-prompted",
        character_score=71,
        capacity_score=None,
        final_score=71,
        decision="ELIGIBLE",
        recommended_amount=3000,
        computed_at=datetime.now(timezone.utc),
        is_current=True,
    )
    component = ScoreComponent(
        score_profile_id=profile.id,
        axis="character",
        component_name="testimony_pool",
        raw_value="3 category-level testimonies",
        contribution=71,
        weight=0.15,
    )
    breakdown = ScoreComputationResult(
        profile=profile,
        components=[component],
        axis_note="capacity axis unavailable - character only",
    )

    # This should not raise an exception (privacy filter should still work)
    explanation = await GeminiExplanationProvider().generate(
        breakdown, 
        "farmer", 
        "Swahili"
    )

    assert explanation.strip()
    assert "Amina Wanjiku" not in explanation
    assert "NATIONAL-12345" not in explanation
