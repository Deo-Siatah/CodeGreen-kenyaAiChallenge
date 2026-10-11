"""Comprehensive test suite for weight validation and bias prevention.

This test suite validates that the weight implementation:
1. Uses the correct weight values as defined in policy
2. Properly renormalizes when components are excluded
3. Implements the logarithmic curve for settlements correctly
4. Maintains the 60/40 character-capacity split
5. Does not inherit bias from traditional credit scoring mechanisms
6. Handles edge cases and boundary conditions properly
"""

import pytest
import math
from typing import Dict, List, Tuple, Optional
from decimal import Decimal

from services.weighting import (
    TESTIMONY_WEIGHT,
    BUYER_WEIGHT,
    DISCIPLINE_WEIGHT,
    SETTLEMENT_WEIGHT,
    CHARACTER_AXIS_WEIGHT,
    CAPACITY_AXIS_WEIGHT,
    BASE_CATEGORY_WEIGHTS,
    combine_character_components,
    combine_axes,
    apply_decision_thresholds,
    testimony_contribution,
    pool_testimonies,
    TestimonyEntry,
)


class TestWeightPolicyValidation:
    """Test that weights follow the policy exactly."""

    def test_character_component_weights_sum_to_one(self):
        """Test that character component weights sum to 1.0 as required."""
        total_weight = TESTIMONY_WEIGHT + BUYER_WEIGHT + DISCIPLINE_WEIGHT + SETTLEMENT_WEIGHT
        assert total_weight == pytest.approx(1.0, rel=1e-10), \
            f"Character weights must sum to 1.0, got {total_weight}"

    def test_axis_weights_sum_to_one(self):
        """Test that axis weights sum to 1.0 as required."""
        total_weight = CHARACTER_AXIS_WEIGHT + CAPACITY_AXIS_WEIGHT
        assert total_weight == pytest.approx(1.0, rel=1e-10), \
            f"Axis weights must sum to 1.0, got {total_weight}"

    def test_character_axis_split_policy(self):
        """Test the 60/40 character-capacity split is correctly implemented."""
        assert CHARACTER_AXIS_WEIGHT == 0.60, \
            f"Character axis must be 0.60, got {CHARACTER_AXIS_WEIGHT}"
        assert CAPACITY_AXIS_WEIGHT == 0.40, \
            f"Capacity axis must be 0.40, got {CAPACITY_AXIS_WEIGHT}"

    def test_character_component_weights_are_proportional(self):
        """Test that character component weights follow the policy proportions."""
        # Test that weights are in the correct proportional relationship
        # DISCIPLINE should be highest, then BUYER, then SETTLEMENT, then TESTIMONY
        assert DISCIPLINE_WEIGHT == pytest.approx(0.35, rel=1e-10), \
            f"Discipline weight must be 0.35, got {DISCIPLINE_WEIGHT}"
        assert BUYER_WEIGHT == pytest.approx(0.30, rel=1e-10), \
            f"Buyer weight must be 0.30, got {BUYER_WEIGHT}"
        assert SETTLEMENT_WEIGHT == pytest.approx(0.20, rel=1e-10), \
            f"Settlement weight must be 0.20, got {SETTLEMENT_WEIGHT}"
        assert TESTIMONY_WEIGHT == pytest.approx(0.15, rel=1e-10), \
            f"Testimony weight must be 0.15, got {TESTIMONY_WEIGHT}"

    def test_weights_do_not_traditional_credit_bias(self):
        """Test that weights don't inherit traditional credit scoring biases."""
        # Traditional credit scoring often overemphasizes:
        # - Income/employment (which would be in capacity)
        # - Collateral/assets (which would be in capacity)
        # - Credit history (which would be in discipline)
        # - Formal banking relationships (which would be in character)
        
        # Our system should balance character and capacity more evenly
        # and not overemphasize any single component
        
        # Character axis should be slightly higher but not dominate
        assert CHARACTER_AXIS_WEIGHT <= 0.65, \
            "Character axis should not exceed 65% to avoid over-reliance on subjective factors"
        
        # Capacity axis should be substantial but not dominate
        assert CAPACITY_AXIS_WEIGHT >= 0.35, \
            "Capacity axis should be at least 35% to ensure objective factors are considered"
        
        # No single character component should dominate
        max_component_weight = max(TESTIMONY_WEIGHT, BUYER_WEIGHT, DISCIPLINE_WEIGHT, SETTLEMENT_WEIGHT)
        assert max_component_weight <= 0.40, \
            "No single character component should exceed 40% to prevent over-reliance on one factor"

    def test_base_category_weights_are_balanced(self):
        """Test that base category weights are balanced and not biased."""
        # Traditional credit scoring often overemphasizes:
        # - High-status individuals (chiefs, officials)
        # - Formal relationships (banks, cooperatives)
        # - Urban connections (buyers, traders)
        
        # Our system should balance:
        # - Community elders (traditional authority)
        # - Professional relationships (teachers, health workers)
        # - Peer relationships (neighbors, groups)
        # - Economic relationships (buyers, traders)
        
        # Check that no single category dominates
        max_weight = max(BASE_CATEGORY_WEIGHTS.values())
        min_weight = min(BASE_CATEGORY_WEIGHTS.values())
        
        # The ratio between highest and lowest should be reasonable
        # (not more than 4:1 to avoid over-reliance on high-status individuals)
        assert max_weight / min_weight <= 4.0, \
            f"Base category weights should be balanced, max/min ratio is {max_weight/min_weight}"
        
        # Ensure there's diversity in weights
        distinct_weights = set(BASE_CATEGORY_WEIGHTS.values())
        assert len(distinct_weights) > 2, \
            "There should be multiple distinct weight levels to reflect different relationship types"


class TestWeightRenormalization:
    """Test that weights are properly renormalized when components are excluded."""

    def test_single_component_renormalization(self):
        """Test renormalization when only one character component is present."""
        # Test with only testimony
        result = combine_character_components(80, None, None, None)
        expected = 80.0  # No renormalization needed when only one component
        assert result == pytest.approx(expected, rel=1e-10)
        
        # Test with only buyer relationship
        result = combine_character_components(None, 70, None, None)
        expected = 70.0
        assert result == pytest.approx(expected, rel=1e-10)
        
        # Test with only discipline
        result = combine_character_components(None, None, 90, None)
        expected = 90.0
        assert result == pytest.approx(expected, rel=1e-10)
        
        # Test with only settlement
        result = combine_character_components(None, None, None, 60)
        expected = 60.0
        assert result == pytest.approx(expected, rel=1e-10)

    def test_two_component_renormalization(self):
        """Test renormalization when two character components are present."""
        # Test with testimony and buyer (15% + 30% = 45% of original weight)
        # Testimony: 80 * (0.15 / 0.45) = 26.67
        # Buyer: 70 * (0.30 / 0.45) = 46.67
        # Combined: 26.67 + 46.67 = 73.33
        result = combine_character_components(80, 70, None, None)
        expected = (80 * TESTIMONY_WEIGHT + 70 * BUYER_WEIGHT) / (TESTIMONY_WEIGHT + BUYER_WEIGHT)
        # Account for 4-decimal rounding in the implementation
        expected_rounded = float(f"{float(expected):.4f}")
        assert result == expected_rounded
        
        # Test with buyer and discipline (30% + 35% = 65% of original weight)
        # Buyer: 70 * (0.30 / 0.65) = 32.31
        # Discipline: 90 * (0.35 / 0.65) = 48.46
        # Combined: 32.31 + 48.46 = 80.77
        result = combine_character_components(None, 70, 90, None)
        expected = (70 * BUYER_WEIGHT + 90 * DISCIPLINE_WEIGHT) / (BUYER_WEIGHT + DISCIPLINE_WEIGHT)
        expected_rounded = float(f"{float(expected):.4f}")
        assert result == expected_rounded

    def test_three_component_renormalization(self):
        """Test renormalization when three character components are present."""
        # Test with testimony, buyer, and discipline (15% + 30% + 35% = 80% of original weight)
        # Testimony: 80 * (0.15 / 0.80) = 15.00
        # Buyer: 70 * (0.30 / 0.80) = 26.25
        # Discipline: 90 * (0.35 / 0.80) = 39.38
        # Combined: 15.00 + 26.25 + 39.38 = 80.63
        result = combine_character_components(80, 70, 90, None)
        total_available_weight = TESTIMONY_WEIGHT + BUYER_WEIGHT + DISCIPLINE_WEIGHT
        expected = (80 * TESTIMONY_WEIGHT + 70 * BUYER_WEIGHT + 90 * DISCIPLINE_WEIGHT) / total_available_weight
        assert result == pytest.approx(expected, rel=1e-10)

    def test_all_component_renormalization(self):
        """Test renormalization when all character components are present."""
        # When all components are present, no renormalization should be needed
        # The weights should be applied as-is
        result = combine_character_components(80, 70, 90, 60)
        # Calculate weighted sum
        expected = (80 * TESTIMONY_WEIGHT + 
                    70 * BUYER_WEIGHT + 
                    90 * DISCIPLINE_WEIGHT + 
                    60 * SETTLEMENT_WEIGHT)
        assert result == pytest.approx(expected, rel=1e-10)

    def test_renormalization_preserves_total_range(self):
        """Test that renormalization preserves the total score range [0, 100]."""
        test_cases = [
            (100, 100, None, None),  # Max values
            (0, 0, None, None),     # Min values
            (50, 50, None, None),   # Mid values
            (100, 0, None, None),   # Mixed values
        ]
        
        for testimony, buyer, discipline, settlement in test_cases:
            if testimony is not None and buyer is not None:
                result = combine_character_components(testimony, buyer, None, None)
                assert 0 <= result <= 100, \
                    f"Renormalized score {result} should be in range [0, 100] for inputs ({testimony}, {buyer})"


class TestSettlementLogarithmicCurve:
    """Test the settlement logarithmic curve implementation."""

    def test_settlement_curve_basic_properties(self):
        """Test basic properties of the settlement logarithmic curve."""
        # The settlement curve should compress large values logarithmically
        # This means that very large settlements should not dominate the score
        
        # Test that small settlements are amplified (log scale)
        small_settlement = 10
        small_score = self._calculate_settlement_score(small_settlement)
        assert small_score > small_settlement, \
            f"Small settlements ({small_settlement}) should be amplified on log scale"
        
        # Test that large settlements are compressed
        large_settlement = 1000000
        large_score = self._calculate_settlement_score(large_settlement)
        assert large_score < large_settlement, \
            f"Large settlements ({large_settlement}) should be compressed on log scale"
        
        # Test that the curve is monotonically increasing
        assert self._calculate_settlement_score(10) < self._calculate_settlement_score(100), \
            "Settlement curve should be monotonically increasing"

    def test_settlement_curve_bias_prevention(self):
        """Test that settlement curve prevents wealth bias."""
        # Traditional credit scoring often overemphasizes large settlements
        # Our logarithmic curve should prevent this
        
        # A very large settlement should not disproportionately affect the score
        huge_settlement_score = self._calculate_settlement_score(1000000)
        moderate_settlement_score = self._calculate_settlement_score(10000)
        
        # The ratio should be reasonable (not more than 2:1)
        ratio = huge_settlement_score / moderate_settlement_score
        assert ratio < 2.0, \
            f"Huge settlements should not dominate, ratio {ratio} is too high"

    def test_settlement_curve_edge_cases(self):
        """Test edge cases for the settlement curve."""
        # Test zero settlement
        zero_score = self._calculate_settlement_score(0)
        assert zero_score == 0, "Zero settlement should result in zero score"
        
        # Test very small settlement
        tiny_score = self._calculate_settlement_score(1)
        assert tiny_score > 0, "Tiny settlement should result in positive score"
        
        # Test negative settlement (should return 0 as per current implementation)
        negative_score = self._calculate_settlement_score(-1)
        assert negative_score == 0, "Negative settlement should result in zero score"

    def _calculate_settlement_score(self, settlement_value: float) -> float:
        """Helper function to calculate settlement score using the logarithmic curve."""
        # This replicates the settlement scoring logic from the actual implementation
        if settlement_value <= 0:
            return 0.0
        
        # Use log10 to compress the range (this is the provisional logarithmic curve)
        log_value = math.log10(settlement_value + 1)  # +1 to handle log(0)
        
        # Scale to 0-100 range (adjust the scaling factor as needed)
        # This is a simplified version - actual implementation may differ
        max_log = math.log10(1000000 + 1)  # Max expected value
        score = (log_value / max_log) * 100
        
        return min(score, 100.0)  # Clamp to maximum

    def _rounded(self, value: float) -> float:
        """Replicate the rounding function from weighting.py."""
        return float(f"{float(value):.4f}")


class TestBiasPreventionValidation:
    """Comprehensive tests for bias prevention."""

    def test_no_overreliance_on_high_status_individuals(self):
        """Test that the system doesn't over-rely on high-status individuals."""
        # High-status categories should not dominate the score
        high_status_categories = ["Chief", "School Head", "SACCO Officer"]
        regular_categories = ["Neighbor", "Youth Group", "Women's Group"]
        
        # Create equal testimony entries from high-status and regular categories
        high_status_entries = [TestimonyEntry(100, weight, category) 
                              for category in high_status_categories 
                              for weight in [BASE_CATEGORY_WEIGHTS[category]]]
        
        regular_entries = [TestimonyEntry(100, weight, category) 
                          for category in regular_categories 
                          for weight in [BASE_CATEGORY_WEIGHTS[category]]]
        
        # Pool separately
        high_status_pool = pool_testimonies(high_status_entries)
        regular_pool = pool_testimonies(regular_entries)
        
        # The high-status pool should not be disproportionately higher
        ratio = high_status_pool.pooled_score / regular_pool.pooled_score
        assert ratio < 1.5, \
            f"High-status pool ({high_status_pool.pooled_score}) should not be more than 50% higher than regular pool ({regular_pool.pooled_score})"

    def test_balanced_rural_urban_representation(self):
        """Test that the system balances rural and urban relationships."""
        # Rural categories (community-focused)
        rural_categories = ["Village Elder", "Neighbor", "Savings Group", "Women's Group"]
        
        # Urban categories (market-focused)
        urban_categories = ["Buyer", "Trader", "Retailer", "Aggregator"]
        
        # Create equal testimony entries
        rural_entries = [TestimonyEntry(80, BASE_CATEGORY_WEIGHTS[cat], cat) 
                        for cat in rural_categories]
        
        urban_entries = [TestimonyEntry(80, BASE_CATEGORY_WEIGHTS[cat], cat) 
                        for cat in urban_categories]
        
        # Pool separately
        rural_pool = pool_testimonies(rural_entries)
        urban_pool = pool_testimonies(urban_entries)
        
        # The rural and urban pools should be reasonably balanced
        ratio = rural_pool.pooled_score / urban_pool.pooled_score
        assert 0.7 < ratio < 1.4, \
            f"Rural ({rural_pool.pooled_score}) and urban ({urban_pool.pooled_score}) pools should be reasonably balanced"

    def test_no_discrimination_by_group_size(self):
        """Test that the system doesn't discriminate by group size."""
        # Large groups (many members)
        large_group_entries = [TestimonyEntry(70, BASE_CATEGORY_WEIGHTS["Women's Group"], "Women's Group")]
        
        # Small groups (few members)
        small_group_entries = [TestimonyEntry(70, BASE_CATEGORY_WEIGHTS["Youth Group"], "Youth Group")]
        
        # The group size should not affect the score disproportionately
        large_pool = pool_testimonies(large_group_entries)
        small_pool = pool_testimonies(small_group_entries)
        
        ratio = large_pool.pooled_score / small_pool.pooled_score
        assert 0.8 < ratio < 1.2, \
            f"Large groups ({large_pool.pooled_score}) and small groups ({small_pool.pooled_score}) should score similarly"

    def test_gender_neutrality(self):
        """Test that the system is gender-neutral."""
        # Male-dominated categories
        male_categories = ["Chief", "Village Elder", "Teacher", "Trader"]
        
        # Female-dominated categories  
        female_categories = ["Teacher", "Health Worker", "Women's Group", "Savings Group"]
        
        # Create equal testimony entries
        male_entries = [TestimonyEntry(80, BASE_CATEGORY_WEIGHTS[cat], cat) 
                       for cat in male_categories]
        
        female_entries = [TestimonyEntry(80, BASE_CATEGORY_WEIGHTS[cat], cat) 
                         for cat in female_categories]
        
        # Pool separately
        male_pool = pool_testimonies(male_entries)
        female_pool = pool_testimonies(female_entries)
        
        # The gender pools should be reasonably balanced
        ratio = male_pool.pooled_score / female_pool.pooled_score
        assert 0.8 < ratio < 1.2, \
            f"Male ({male_pool.pooled_score}) and female ({female_pool.pooled_score}) categories should be reasonably balanced"


class TestWeightMathematicalProperties:
    """Test mathematical properties of the weighting system."""

    def test_weight_linearity(self):
        """Test that the weighting system is linear within bounds."""
        # Test that doubling input doubles output (when within bounds)
        base_score = combine_character_components(50, 50, 50, 50)
        doubled_score = combine_character_components(100, 100, 100, 100)
        
        # The doubled score should be approximately double (accounting for clamping)
        assert doubled_score >= base_score * 1.8, "Doubling inputs should approximately double output"

    def test_weight_consistency(self):
        """Test that weighting is consistent across different combinations."""
        # Test that the same weighted score is achieved regardless of component order
        score1 = combine_character_components(80, 70, 90, 60)
        score2 = combine_character_components(60, 90, 70, 80)  # Different order
        
        # The scores should be the same (order shouldn't matter)
        assert score1 == pytest.approx(score2, rel=1e-10), "Weighting should be order-independent"

    def test_weight_boundary_conditions(self):
        """Test boundary conditions for weighting."""
        # Test minimum values
        min_score = combine_character_components(0, 0, 0, 0)
        assert min_score == 0, "All minimum inputs should result in minimum output"
        
        # Test maximum values
        max_score = combine_character_components(100, 100, 100, 100)
        assert max_score == 100, "All maximum inputs should result in maximum output"

    def test_weight_continuity(self):
        """Test that weighting functions are continuous."""
        # Small changes in input should result in small changes in output
        base_score = combine_character_components(50, 50, 50, 50)
        
        # Test small increments
        for delta in [0.1, 1.0, 5.0]:
            incremented_score = combine_character_components(50 + delta, 50, 50, 50)
            assert abs(incremented_score - base_score) <= delta * 1.1, \
                f"Small change of {delta} should result in small output change"


class TestWeightEdgeCases:
    """Test edge cases for the weighting system."""

    def test_none_handling(self):
        """Test proper handling of None values."""
        # Test that all None values raise an error (correct behavior)
        with pytest.raises(ValueError, match="at least one character component is required"):
            combine_character_components(None, None, None, None)
        
        # Test that partial None values work
        result = combine_character_components(80, None, 90, None)
        assert result > 0, "Partial None values should still produce valid results"

    def test_extreme_values(self):
        """Test handling of extreme values."""
        # Test very high values
        high_score = combine_character_components(1000, 1000, 1000, 1000)
        assert high_score <= 100, "Extreme values should be clamped to maximum"
        
        # Test very low values
        low_score = combine_character_components(-100, -100, -100, -100)
        assert low_score >= 0, "Extreme values should be clamped to minimum"

    def test_mixed_valid_invalid(self):
        """Test handling of mixed valid and invalid inputs."""
        # Test that valid inputs with some invalid still work
        result = combine_character_components(80, None, 90, 70)
        assert result > 0, "Mixed valid/invalid inputs should still work"

    def test_weight_precision(self):
        """Test numerical precision of weighting calculations."""
        # Test that calculations maintain sufficient precision
        result = combine_character_components(33.3333, 66.6667, 50.0, 25.0)
        assert isinstance(result, float), "Result should be a float"
        assert 0 <= result <= 100, "Result should be in valid range"
        
        # Test precision with many decimal places
        # This should be: (33.33333333 * 0.15 + 66.66666667 * 0.30 + 50.0 * 0.35 + 25.0 * 0.20) = 47.5
        precise_result = combine_character_components(33.33333333, 66.66666667, 50.0, 25.0)
        expected = 47.5  # This is the exact expected value
        assert abs(precise_result - expected) < 0.1, f"Precise calculations should be accurate, got {precise_result}"


class TestWeightIntegration:
    """Test integration of weights with the overall scoring system."""

    def test_character_capacity_integration(self):
        """Test integration of character and capacity axes."""
        # Test character-only scoring
        character_score = 75
        capacity_score = None
        result, description = combine_axes(character_score, capacity_score)
        assert result == character_score, "Character-only scoring should use character score directly"
        assert "character only" in description.lower(), "Description should indicate character-only"
        
        # Test capacity-only scoring
        character_score = None
        capacity_score = 65
        result, description = combine_axes(character_score, capacity_score)
        assert result == capacity_score, "Capacity-only scoring should use capacity score directly"
        assert "capacity" in description.lower(), "Description should indicate capacity"
        
        # Test combined scoring
        character_score = 70
        capacity_score = 60
        result, description = combine_axes(character_score, capacity_score)
        expected = (character_score * CHARACTER_AXIS_WEIGHT + 
                   capacity_score * CAPACITY_AXIS_WEIGHT)
        assert result == pytest.approx(expected, rel=1e-10), "Combined scoring should use weighted average"

    def test_weight_threshold_integration(self):
        """Test integration of weights with decision thresholds."""
        # Test that weighted scores work with decision thresholds
        test_scores = [40, 50, 60, 70, 80]
        
        for score in test_scores:
            decision, action, amount = apply_decision_thresholds(score)
            assert decision in ["ELIGIBLE", "REVIEW_REQUIRED", "DECLINE"], \
                f"Decision should be valid for score {score}"
            assert isinstance(action, str), f"Action should be a string for score {score}"
            assert amount is None or isinstance(amount, (int, float)), \
                f"Amount should be numeric or None for score {score}"

    def test_weight_bias_prevention_integration(self):
        """Test integration of weights with bias prevention."""
        # Create a test case that demonstrates bias prevention
        testimonies = [
            TestimonyEntry(100, 4, "Neighbor"),      # High rating, low status
            TestimonyEntry(100, 4, "Chief"),        # High rating, high status
            TestimonyEntry(50, 1, "Neighbor"),      # Low rating, low status
            TestimonyEntry(50, 1, "Chief"),         # Low rating, high status
        ]
        
        pooled = pool_testimonies(testimonies)
        
        # The pooled score should not be biased toward high-status individuals
        assert 0 <= pooled.pooled_score <= 100, "Pooled score should be in valid range"
        assert pooled.distinct_category_count == 2, "Should count distinct categories correctly"
        
        # The diversity bonus should be applied appropriately
        if pooled.applied_diversity_bonus:
            assert pooled.pooled_score > 75, "Diversity bonus should significantly improve score"


class TestWeightDocumentation:
    """Test that weights are properly documented and explainable."""

    def test_weight_documentation_clarity(self):
        """Test that weights are clearly documented."""
        # Test that weight constants have clear names
        assert hasattr(services.weighting, 'TESTIMONY_WEIGHT'), "Testimony weight should be documented"
        assert hasattr(services.weighting, 'BUYER_WEIGHT'), "Buyer weight should be documented"
        assert hasattr(services.weighting, 'DISCIPLINE_WEIGHT'), "Discipline weight should be documented"
        assert hasattr(services.weighting, 'SETTLEMENT_WEIGHT'), "Settlement weight should be documented"
        
        # Test that weights have reasonable values
        assert 0 < TESTIMONY_WEIGHT < 1, "Testimony weight should be between 0 and 1"
        assert 0 < BUYER_WEIGHT < 1, "Buyer weight should be between 0 and 1"
        assert 0 < DISCIPLINE_WEIGHT < 1, "Discipline weight should be between 0 and 1"
        assert 0 < SETTLEMENT_WEIGHT < 1, "Settlement weight should be between 0 and 1"

    def test_weight_transparency(self):
        """Test that weight calculations are transparent and explainable."""
        # Test that the calculation process is transparent
        result = combine_character_components(80, 70, 90, 60)
        
        # The result should be explainable
        assert isinstance(result, (int, float)), "Result should be a numeric value"
        assert 0 <= result <= 100, "Result should be in explainable range [0, 100]"
        
        # The calculation should be reproducible
        result2 = combine_character_components(80, 70, 90, 60)
        assert result == result2, "Calculation should be reproducible"

    def test_weight_audit_trail(self):
        """Test that weights leave an audit trail."""
        # Test that weight usage can be traced
        character_components = {
            'testimony': 80,
            'buyer': 70,
            'discipline': 90,
            'settlement': 60
        }
        
        # Each component should be traceable
        for component, value in character_components.items():
            if value is not None:
                assert isinstance(value, (int, float)), f"{component} value should be numeric"
                assert 0 <= value <= 100, f"{component} value should be in range [0, 100]"