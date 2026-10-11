import pytest

from services.weighting import (
    BASE_CATEGORY_WEIGHTS,
    apply_decision_thresholds,
    combine_axes,
    combine_character_components,
    pool_testimonies,
    response_scale_to_value,
    testimony_contribution,
    TestimonyEntry,
)


def test_response_scale_maps_four_point_scale():
    assert response_scale_to_value(1) == 0
    assert response_scale_to_value(2) == pytest.approx(33.3333)
    assert response_scale_to_value(3) == pytest.approx(66.6667)
    assert response_scale_to_value(4) == 100
    with pytest.raises(ValueError):
        response_scale_to_value(0)
    with pytest.raises(ValueError):
        response_scale_to_value(5)


def test_legacy_category_weights_and_worked_testimony_example():
    assert BASE_CATEGORY_WEIGHTS["Chief"] == 4
    assert BASE_CATEGORY_WEIGHTS["Neighbor"] == 1
    assert BASE_CATEGORY_WEIGHTS["School Head"] == 4
    assert BASE_CATEGORY_WEIGHTS["Savings Group"] == 4
    assert testimony_contribution(4, 1, 1) == 100
    pooled = pool_testimonies(
        [
            TestimonyEntry(100, 1, "Neighbor"),
            TestimonyEntry(100, 1, "Neighbor"),
            TestimonyEntry(testimony_contribution(2, 1, 1), 1, "Neighbor"),
        ]
    )
    assert pooled.pooled_score == pytest.approx(77.7777, abs=0.01)


def test_pooling_diversity_bonus_and_cap():
    same_category = pool_testimonies(
        [TestimonyEntry(80, 1, "Neighbor"), TestimonyEntry(90, 1, "Neighbor")]
    )
    assert same_category.applied_diversity_bonus is False
    diverse = pool_testimonies(
        [
            TestimonyEntry(80, 1, "Chief"),
            TestimonyEntry(90, 1, "Buyer"),
            TestimonyEntry(100, 1, "Chama"),
        ]
    )
    assert diverse.applied_diversity_bonus is True
    assert diverse.distinct_category_count == 3
    assert diverse.pooled_score == 99
    capped = pool_testimonies(
        [
            TestimonyEntry(100, 1, "Chief"),
            TestimonyEntry(100, 1, "Buyer"),
            TestimonyEntry(100, 1, "Chama"),
        ]
    )
    assert capped.pooled_score == 100


def test_empty_pool_raises():
    with pytest.raises(ValueError):
        pool_testimonies([])


def test_character_components_renormalize_available_weights():
    assert combine_character_components(80, None, 40, None) == pytest.approx(52.0)
    with pytest.raises(ValueError):
        combine_character_components(None, None, None, None)


def test_axes_without_capacity_and_with_capacity():
    assert combine_axes(70, None) == (70, "capacity axis unavailable - character only")
    assert combine_axes(70, 50) == (pytest.approx(62), "combined")


def test_decision_threshold_boundaries():
    assert apply_decision_thresholds(74.99) == (
        "ELIGIBLE",
        "APPROVE_LEVEL_1",
        3000,
    )
    assert apply_decision_thresholds(75) == ("ELIGIBLE", "APPROVE_LEVEL_2", 5000)
    assert apply_decision_thresholds(59.99) == (
        "REVIEW_REQUIRED",
        "Manual review required",
        None,
    )
    assert apply_decision_thresholds(60) == ("ELIGIBLE", "APPROVE_LEVEL_1", 3000)
    assert apply_decision_thresholds(44.99) == (
        "DECLINE",
        "Insufficient community trust",
        None,
    )
    assert apply_decision_thresholds(45) == (
        "REVIEW_REQUIRED",
        "Manual review required",
        None,
    )


def test_testimony_contribution_with_buyer_types():
    """Test that testimony_contribution works identically for buyer-shaped data."""
    # Test with Buyer type (should work like any other category)
    buyer_contribution = testimony_contribution(4, 4, 1.0)  # max rating, max weight, neutral credibility
    assert buyer_contribution == 400  # 4 * 1 * 100 = 400
    
    # Test with Trader type
    trader_contribution = testimony_contribution(3, 3, 1.0)  # mid rating, mid weight, neutral credibility
    assert trader_contribution == pytest.approx(200, abs=0.01)  # 3 * 1 * 66.67 = 200
    
    # Test with credibility adjustment (should work same for buyer types)
    high_credibility = testimony_contribution(4, 4, 1.2)  # boosted credibility
    assert high_credibility > 400  # Should be boosted above max
    
    low_credibility = testimony_contribution(4, 4, 0.8)  # reduced credibility
    assert low_credibility < 400  # Should be reduced below max


def test_pool_testimonies_with_buyer_types():
    """Test that pool_testimonies works identically when fed buyer-shaped data."""
    # Test pooling buyer testimonies with same category (no diversity bonus)
    same_category_pool = pool_testimonies([
        TestimonyEntry(340, 4, "Buyer"),  # 4 * 4 * 85 = 340
        TestimonyEntry(340, 4, "Buyer"),  # 4 * 4 * 85 = 340
    ])
    assert same_category_pool.applied_diversity_bonus is False
    assert same_category_pool.pooled_score == pytest.approx(85, abs=0.01)  # (340 + 340) / 8 = 85
    
    # Test pooling buyer testimonies with different categories (diversity bonus)
    diverse_category_pool = pool_testimonies([
        TestimonyEntry(320, 4, "Buyer"),    # 4 * 4 * 80 = 320
        TestimonyEntry(240, 3, "Trader"),   # 3 * 3 * 80 = 240
        TestimonyEntry(200, 2, "Retailer"),  # 2 * 2 * 100 = 200
    ])
    assert diverse_category_pool.applied_diversity_bonus is True
    assert diverse_category_pool.distinct_category_count == 3
    assert diverse_category_pool.pooled_score > 90  # Should be boosted by diversity bonus
    
    # Test that the function works with any valid category from BASE_CATEGORY_WEIGHTS
    for category in BASE_CATEGORY_WEIGHTS.keys():
        entry = TestimonyEntry(50, BASE_CATEGORY_WEIGHTS[category], category)
        # Should not raise an exception
        pool_testimonies([entry])


def test_pool_testimonies_clamping():
    """Test that pooled_score is clamped to [0, 100] even with high credibility."""
    # Test with high credibility (1.5) and max rating (4)
    # This should result in: 4 * 4 * 1.5 * 100 = 2400, which should be clamped to 100
    entry = TestimonyEntry(2400, 4, "Buyer")  # 4 * 4 * 1.5 * 100 = 2400
    result = pool_testimonies([entry])
    assert result.pooled_score == 100  # Should be clamped to maximum
    
    # Test with negative contribution
    entry = TestimonyEntry(-1000, 4, "Buyer")
    result = pool_testimonies([entry])
    assert result.pooled_score == 0  # Should be clamped to minimum
