"""Pure scoring functions for the provisional Hifadhi scorecard.

This module intentionally has no database or service imports. Keeping the math
here makes the policy easy to review and the edge cases cheap to test.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import log10

# Cold-start category weights ported exactly from weighting_service.py.
BASE_CATEGORY_WEIGHTS: dict[str, float] = {
    "Chief": 4.0,
    "Assistant Chief": 3.0,
    "Village Elder": 3.0,
    "Religious Leader": 3.0,
    "Teacher": 3.0,
    "School Head": 4.0,
    "Health Worker": 3.0,
    "Agrovet Owner": 3.0,
    "Cooperative Officer": 4.0,
    "SACCO Officer": 4.0,
    "Neighbor": 1.0,
    "Buyer": 4.0,
    "Trader": 3.0,
    "Retailer": 3.0,
    "Aggregator": 4.0,
    "Chama": 3.0,
    "Savings Group": 4.0,
    "Youth Group": 3.0,
    "Women's Group": 3.0,
}
DEFAULT_UNKNOWN_WEIGHT = 1.0

# Character-axis weights from scoring.md section 3.1. Missing components are
# excluded and the remaining weights are renormalized by combine_character_components.
TESTIMONY_WEIGHT = 0.15
BUYER_WEIGHT = 0.30
DISCIPLINE_WEIGHT = 0.35
SETTLEMENT_WEIGHT = 0.20

# Settlement values span a wide range. This provisional logarithmic curve
# compresses that range sensibly without choosing an arbitrary hard cap for
# ordinary values; revisit it when real settlement distributions are available.


# Section 4 leaves the 60/40 character-capacity split as a provisional open
# question. Keep the policy visible here so changing it does not alter logic.
CHARACTER_AXIS_WEIGHT = 0.60
CAPACITY_AXIS_WEIGHT = 0.40


def _rounded(value: float) -> float:
    """Round score math to a stable 4-decimal precision used by the policy."""
    return float(f"{float(value):.4f}")


@dataclass(frozen=True)
class TestimonyEntry:
    __test__ = False

    contribution: float
    weight: float
    category: str


@dataclass(frozen=True)
class PooledResult:
    __test__ = False

    pooled_score: float
    distinct_category_count: int
    applied_diversity_bonus: bool


def response_scale_to_value(rating: int) -> float:
    """Map the forced-choice 1-4 response scale to 0-100."""
    if rating not in {1, 2, 3, 4}:
        raise ValueError("rating must be one of 1, 2, 3, or 4")
    return _rounded((rating - 1) / 3 * 100)


response_scale_to_value.__test__ = False


def testimony_contribution(
    rating: int, base_weight: float, credibility_score: float
) -> float:
    """Apply category weight and verifier credibility to one rating."""
    return _rounded(base_weight * credibility_score * response_scale_to_value(rating))


testimony_contribution.__test__ = False


def settlement_value(value: float | None) -> float:
    """Convert a settlement value into a bounded 0-100 score."""
    if value is None:
        return 0.0
    return _rounded(min(100.0, 25.0 * log10(1.0 + max(0.0, float(value)))))


settlement_value.__test__ = False


# This provisional discipline curve rewards recent, repeated contributions.
# The 60-day decay boundary and 0.8 multiplier need calibration against actual
# repayment outcomes before they should be treated as a settled policy.
DISCIPLINE_RECENCY_DAYS = 60
DISCIPLINE_RECENCY_DECAY = 0.8


def discipline_value(
    cycles: int | None,
    last_contribution_date: date | None,
    reference_date: date,
) -> float:
    """Score contribution cycles, decaying stale activity after 60 days."""
    score = min(100.0, float(cycles or 0) * 15.0)
    if (
        last_contribution_date is not None
        and (reference_date - last_contribution_date).days > DISCIPLINE_RECENCY_DAYS
    ):
        score *= DISCIPLINE_RECENCY_DECAY
    return _rounded(score)


discipline_value.__test__ = False


def pool_testimonies(entries: list[TestimonyEntry]) -> PooledResult:
    """Weighted-average testimonies and apply one diversity bonus if earned."""
    if not entries:
        raise ValueError("cannot pool an empty testimony list")
    total_weight = sum(entry.weight for entry in entries)
    if total_weight == 0:
        raise ValueError("testimony weights must not sum to zero")
    pooled_score = sum(entry.contribution for entry in entries) / total_weight
    category_count = len({entry.category for entry in entries})
    bonus = category_count >= 3
    if bonus:
        pooled_score = min(100.0, pooled_score * 1.1)
    pooled_score = _rounded(pooled_score)
    # Clamp pooled_score to [0, 100]
    pooled_score = max(0.0, min(100.0, pooled_score))
    return PooledResult(pooled_score, category_count, bonus)


pool_testimonies.__test__ = False


def combine_character_components(
    testimony: float | None,
    buyer: float | None,
    discipline: float | None,
    settlement: float | None,
) -> float:
    """Combine available character components with weight renormalization."""
    components = (
        (testimony, TESTIMONY_WEIGHT),
        (buyer, BUYER_WEIGHT),
        (discipline, DISCIPLINE_WEIGHT),
        (settlement, SETTLEMENT_WEIGHT),
    )
    available = [(value, weight) for value, weight in components if value is not None]
    if not available:
        raise ValueError("at least one character component is required")
    total_weight = sum(weight for _, weight in available)
    combined = sum(value * weight for value, weight in available) / total_weight
    result = _rounded(combined)
    # Clamp result to [0, 100]
    return max(0.0, min(100.0, result))


combine_character_components.__test__ = False


def combine_axes(character_score: float | None, capacity_score: float | None) -> tuple[float, str]:
    """Combine character and capacity, or handle cases where one axis is unavailable."""
    if capacity_score is None:
        return _rounded(character_score), "capacity axis unavailable - character only"
    return (
        _rounded(
            character_score * CHARACTER_AXIS_WEIGHT
            + capacity_score * CAPACITY_AXIS_WEIGHT
        ),
        "combined",
    )


combine_axes.__test__ = False


def apply_decision_thresholds(final_score: float) -> tuple[str, str, int | None]:
    """Apply the legacy decision buckets without changing their thresholds."""
    if final_score >= 75:
        return "ELIGIBLE", "APPROVE_LEVEL_2", 5000
    if final_score >= 60:
        return "ELIGIBLE", "APPROVE_LEVEL_1", 3000
    if final_score >= 45:
        return "REVIEW_REQUIRED", "Manual review required", None
    return "DECLINE", "Insufficient community trust", None


apply_decision_thresholds.__test__ = False


def normalize_capacity_score(
    cultivation_continuity_score: float, acreage: float | None
) -> float:
    """Validate an already normalized activity score.

    Callers (FarmActivityProvider implementations) MUST return an already
    per-hectare-normalized continuity score - this function does not normalize
    by acreage itself, it only validates and clamps. Acreage is accepted to
    make that contract explicit, but has no effect on the result.
    """
    if acreage is not None and acreage <= 0:
        raise ValueError("acreage must be positive when supplied")
    return _rounded(max(0.0, min(100.0, float(cultivation_continuity_score))))


normalize_capacity_score.__test__ = False
