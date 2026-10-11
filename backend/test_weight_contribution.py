"""
Test script for different weights contribution in the scoring system.

This script tests how the different weights specified in scoring.md affect the final score.
The scoring system uses these provisional weights:
- Discipline proxies: 35% (highest - most specific behavioral data)
- Buyer relationship: 30% (high - specific transactional data) 
- In-kind settlement: Moderate (bonus signal, not core)
- Community testimony: Lowest of four (corroborating/qualifying signal)

Key test scenarios:
1. Test individual component contributions
2. Test weight sensitivity analysis
3. Test extreme weight scenarios
4. Test component failure scenarios
5. Test weight balance validation

Run: uv run python test_weight_contribution.py --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import sys
import uuid
from typing import Any, Dict, List, Tuple
import httpx


DEFAULT_BASE_URL = "http://localhost:8000"


def step(label: str) -> None:
    print(f"\n{'=' * 60}\n{label}\n{'=' * 60}")


def post(client: httpx.Client, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(path, json=payload)
    print(f"POST {path} -> {response.status_code}")
    if response.status_code >= 400:
        print(response.text)
        response.raise_for_status()
    return response.json()


def get(client: httpx.Client, path: str) -> dict[str, Any]:
    response = client.get(path)
    print(f"GET {path} -> {response.status_code}")
    if response.status_code >= 400:
        print(response.text)
        response.raise_for_status()
    return response.json()


def create_test_farmer(client: httpx.Client, suffix: str = "") -> tuple[dict, str, dict, str]:
    """Create a test farmer and return farmer, farmer_id, farm, farm_id"""
    step(f"Creating test farmer for weight test {suffix}")
    run_id = uuid.uuid4().hex[:10]
    farmer = post(client, "/api/farmers", {
        "full_name": f"Weight Test Farmer {suffix}",
        "national_id": f"WEIGHT-{run_id}-{suffix}",
        "phone": f"+2547{run_id[:8]}",
        "gender": "female",
        "date_of_birth": "1985-04-12",
        "location": "Kiambu",
        "village": "Test Village",
        "sub_county": "Test Sub-County",
        "county": "Kiambu",
        "farming_type": "mixed",
        "years_farming": 6,
    })
    farmer_id = farmer["id"]
    
    farm = post(client, f"/api/farmers/{farmer_id}/farm", {
        "acreage": 1.5,
        "production_type": "crop",
        "latitude": -1.1714,
        "longitude": 36.8356,
    })
    farm_id = farm["id"]
    
    return farmer, farmer_id, farm, farm_id


def create_verifiers(client: httpx.Client, farmer_id: str) -> tuple[str, str, str]:
    """Create trust sources and return their IDs"""
    step("Creating verifiers for weight test")
    
    trust_source = post(client, "/api/trust/sources", {
        "name": "Test Chief Weight",
        "category": "Chief",
        "phone": "+254700000002",
        "national_id": "88888888",
        "location": "Kiambu",
    })
    trust_source_id = trust_source["id"]

    market_actor = post(client, "/api/trust/market-actors", {
        "name": "Test Buyer Weight",
        "actor_type": "Buyer",
        "phone": "+254700000003",
        "location": "Kiambu",
    })
    market_actor_id = market_actor["id"]

    social_group = post(client, "/api/trust/social-groups", {
        "name": "Test Chama Weight",
        "group_type": "Savings Group",
        "location": "Kiambu",
        "formation_year": 2019,
    })
    social_group_id = social_group["id"]

    # Link verifiers to farmer
    post(client, f"/api/farmers/{farmer_id}/link-trust-source", {
        "related_id": trust_source_id,
    })
    post(client, f"/api/farmers/{farmer_id}/link-market-actor", {
        "related_id": market_actor_id,
    })
    post(client, f"/api/farmers/{farmer_id}/link-social-group", {
        "related_id": social_group_id,
    })

    return trust_source_id, market_actor_id, social_group_id


def run_verification_session(client: httpx.Client, farmer_id: str, 
                           trust_rating: int = 4, buyer_rating: int = 4, 
                           group_cycles: int = 5) -> dict[str, Any]:
    """Run a verification session with specified ratings"""
    step(f"Running verification session for farmer {farmer_id}")
    
    session = post(client, "/api/verify/start", {"farmer_id": farmer_id})
    session_id = session["session_id"]
    status = get(client, f"/api/verify/{session_id}/status")
    participants = status["participants"]
    
    by_type = {p["participant_type"]: p["id"] for p in participants}
    
    # Submit responses with correct payload structure for each participant type
    if "trust_source" in by_type:
        post(client, f"/api/verify/{session_id}/respond/{by_type['trust_source']}", {
            "participant_type": "trust_source", "rating": trust_rating,
            "comments": "Test response", "personal_knowledge_flag": True,
        })
    
    if "market_actor" in by_type:
        post(client, f"/api/verify/{session_id}/respond/{by_type['market_actor']}", {
            "participant_type": "market_actor", "reliability_rating": buyer_rating,
            "purchase_frequency": "weekly", "relationship_months": 24,
            "avg_volume_kg": 40,
        })
    
    if "social_group" in by_type:
        post(client, f"/api/verify/{session_id}/respond/{by_type['social_group']}", {
            "participant_type": "social_group", "consecutive_cycles": group_cycles,
            "last_contribution_date": "2026-09-01", "contribution_amount": 500,
        })
    
    # Get final score
    score = get(client, f"/api/verify/{session_id}/result")
    return score


def test_individual_component_contributions(client: httpx.Client) -> None:
    """Test scenario 1: Individual component contributions"""
    step("TEST SCENARIO 1: Individual component contributions")
    
    farmer, farmer_id, farm, farm_id = create_test_farmer(client, "INDIVIDUAL")
    trust_id, buyer_id, group_id = create_verifiers(client, farmer_id)
    
    # Test each component individually
    components = [
        ("Trust Source Only", {"trust_rating": 4, "buyer_rating": 0, "group_cycles": 0}),
        ("Buyer Only", {"trust_rating": 0, "buyer_rating": 4, "group_cycles": 0}),
        ("Social Group Only", {"trust_rating": 0, "buyer_rating": 0, "group_cycles": 10}),
        ("All Components", {"trust_rating": 4, "buyer_rating": 4, "group_cycles": 5}),
    ]
    
    results = {}
    for comp_name, ratings in components:
        score = run_verification_session(client, farmer_id, **ratings)
        final_score = score['score_profile']['final_score']
        character_score = score['score_profile']['character_score']
        results[comp_name] = {
            'final_score': final_score,
            'character_score': character_score,
            'breakdown': score['score_profile'].get('character_breakdown', [])
        }
        print(f"{comp_name}: Final={final_score}, Character={character_score}")
    
    # Analyze contributions
    print("\nComponent Contribution Analysis:")
    trust_only = results["Trust Source Only"]['final_score']
    buyer_only = results["Buyer Only"]['final_score']
    group_only = results["Social Group Only"]['final_score']
    all_components = results["All Components"]['final_score']
    
    # Check if components add up appropriately (not necessarily linear due to weights)
    expected_approximate = trust_only + buyer_only + group_only
    actual = all_components
    
    print(f"Trust only: {trust_only}")
    print(f"Buyer only: {buyer_only}")
    print(f"Group only: {group_only}")
    print(f"Sum of individual: {expected_approximate}")
    print(f"All components together: {actual}")
    print(f"Difference: {actual - expected_approximate}")
    
    # Verify that all components together is better than any single component
    if all_components > max(trust_only, buyer_only, group_only):
        print("✓ Combined score better than individual components")
    else:
        print("✗ Combined score not better than best individual component")
    
    return results


def test_weight_sensitivity_analysis(client: httpx.Client) -> None:
    """Test scenario 2: Weight sensitivity analysis"""
    step("TEST SCENARIO 2: Weight sensitivity analysis")
    
    farmer, farmer_id, farm, farm_id = create_test_farmer(client, "SENSITIVITY")
    trust_id, buyer_id, group_id = create_verifiers(client, farmer_id)
    
    # Test different rating combinations to see weight sensitivity
    test_cases = [
        ("All Low", {"trust_rating": 1, "buyer_rating": 1, "group_cycles": 1}),
        ("All Medium", {"trust_rating": 2, "buyer_rating": 2, "group_cycles": 3}),
        ("All High", {"trust_rating": 4, "buyer_rating": 4, "group_cycles": 10}),
        ("Trust High, Others Low", {"trust_rating": 4, "buyer_rating": 1, "group_cycles": 1}),
        ("Buyer High, Others Low", {"trust_rating": 1, "buyer_rating": 4, "group_cycles": 1}),
        ("Group High, Others Low", {"trust_rating": 1, "buyer_rating": 1, "group_cycles": 10}),
    ]
    
    results = {}
    for case_name, ratings in test_cases:
        score = run_verification_session(client, farmer_id, **ratings)
        final_score = score['score_profile']['final_score']
        character_score = score['score_profile']['character_score']
        results[case_name] = {
            'final_score': final_score,
            'character_score': character_score,
            'breakdown': score['score_profile'].get('character_breakdown', [])
        }
        print(f"{case_name}: Final={final_score}, Character={character_score}")
    
    # Analyze sensitivity
    print("\nWeight Sensitivity Analysis:")
    all_low = results["All Low"]['final_score']
    all_high = results["All High"]['final_score']
    trust_high = results["Trust High, Others Low"]['final_score']
    buyer_high = results["Buyer High, Others Low"]['final_score']
    group_high = results["Group High, Others Low"]['final_score']
    
    print(f"Score range (low to high): {all_low} to {all_high}")
    print(f"Trust high boost: {trust_high - all_low}")
    print(f"Buyer high boost: {buyer_high - all_low}")
    print(f"Group high boost: {group_high - all_low}")
    
    # Check if discipline proxy (group) has highest impact as expected (35% weight)
    expected_highest = "Group High, Others Low"
    actual_highest = max([
        ("Trust High", trust_high),
        ("Buyer High", buyer_high),
        ("Group High", group_high)
    ], key=lambda x: x[1])[0]
    
    if actual_highest == "Group High":
        print("✓ Discipline proxy (group) has highest impact as expected")
    else:
        print(f"✗ Unexpected highest impact: {actual_highest}")
    
    return results


def test_extreme_weight_scenarios(client: httpx.Client) -> None:
    """Test scenario 3: Extreme weight scenarios"""
    step("TEST SCENARIO 3: Extreme weight scenarios")
    
    farmer, farmer_id, farm, farm_id = create_test_farmer(client, "EXTREME")
    trust_id, buyer_id, group_id = create_verifiers(client, farmer_id)
    
    # Test extreme scenarios
    extreme_cases = [
        ("Perfect Scores", {"trust_rating": 4, "buyer_rating": 4, "group_cycles": 20}),
        ("Worst Scores", {"trust_rating": 1, "buyer_rating": 1, "group_cycles": 0}),
        ("Mixed Extremes", {"trust_rating": 4, "buyer_rating": 1, "group_cycles": 20}),
        ("Opposite Mixed", {"trust_rating": 1, "buyer_rating": 4, "group_cycles": 0}),
    ]
    
    results = {}
    for case_name, ratings in extreme_cases:
        score = run_verification_session(client, farmer_id, **ratings)
        final_score = score['score_profile']['final_score']
        character_score = score['score_profile']['character_score']
        results[case_name] = {
            'final_score': final_score,
            'character_score': character_score,
            'breakdown': score['score_profile'].get('character_breakdown', [])
        }
        print(f"{case_name}: Final={final_score}, Character={character_score}")
    
    # Check extreme score boundaries
    perfect = results["Perfect Scores"]['final_score']
    worst = results["Worst Scores"]['final_score']
    mixed = results["Mixed Extremes"]['final_score']
    opposite = results["Opposite Mixed"]['final_score']
    
    print(f"\nExtreme Score Analysis:")
    print(f"Perfect scenario: {perfect}")
    print(f"Worst scenario: {worst}")
    print(f"Mixed extremes: {mixed}")
    print(f"Opposite mixed: {opposite}")
    
    # Check if perfect score is reasonable (should be close to 100)
    if perfect >= 80:
        print("✓ Perfect score is reasonably high")
    else:
        print(f"✗ Perfect score unexpectedly low: {perfect}")
    
    # Check if worst score is reasonable (should be close to 0)
    if worst <= 20:
        print("✓ Worst score is reasonably low")
    else:
        print(f"✗ Worst score unexpectedly high: {worst}")
    
    return results


def test_component_failure_scenarios(client: httpx.Client) -> None:
    """Test scenario 4: Component failure scenarios"""
    step("TEST SCENARIO 4: Component failure scenarios")
    
    farmer, farmer_id, farm, farm_id = create_test_farmer(client, "FAILURE")
    trust_id, buyer_id, group_id = create_verifiers(client, farmer_id)
    
    # Test scenarios where individual components fail
    failure_cases = [
        ("Trust Source Fails (rating 1)", {"trust_rating": 1, "buyer_rating": 4, "group_cycles": 10}),
        ("Buyer Fails (rating 1)", {"trust_rating": 4, "buyer_rating": 1, "group_cycles": 10}),
        ("Group Fails (cycles 0)", {"trust_rating": 4, "buyer_rating": 4, "group_cycles": 0}),
        ("All Fail", {"trust_rating": 1, "buyer_rating": 1, "group_cycles": 0}),
    ]
    
    results = {}
    for case_name, ratings in failure_cases:
        score = run_verification_session(client, farmer_id, **ratings)
        final_score = score['score_profile']['final_score']
        character_score = score['score_profile']['character_score']
        results[case_name] = {
            'final_score': final_score,
            'character_score': character_score,
            'breakdown': score['score_profile'].get('character_breakdown', [])
        }
        print(f"{case_name}: Final={final_score}, Character={character_score}")
    
    # Analyze impact of failures
    print("\nComponent Failure Impact Analysis:")
    trust_fail = results["Trust Source Fails (rating 1)"]['final_score']
    buyer_fail = results["Buyer Fails (rating 1)"]['final_score']
    group_fail = results["Group Fails (cycles 0)"]['final_score']
    all_fail = results["All Fail"]['final_score']
    
    # Compare with baseline (all good)
    baseline = run_verification_session(client, farmer_id, 4, 4, 10)['final_score']
    
    print(f"Baseline (all good): {baseline}")
    print(f"Trust failure impact: {baseline - trust_fail}")
    print(f"Buyer failure impact: {baseline - buyer_fail}")
    print(f"Group failure impact: {baseline - group_fail}")
    print(f"All failure impact: {baseline - all_fail}")
    
    # Check which component failure has biggest impact
    impacts = {
        "Trust": baseline - trust_fail,
        "Buyer": baseline - buyer_fail,
        "Group": baseline - group_fail
    }
    
    biggest_impact = max(impacts.items(), key=lambda x: x[1])
    print(f"Biggest impact from {biggest_impact[0]} failure: {biggest_impact[1]}")
    
    # Verify that group (discipline proxy) has highest impact due to 35% weight
    if biggest_impact[0] == "Group":
        print("✓ Group (discipline proxy) failure has highest impact as expected")
    else:
        print(f"✗ Unexpected biggest impact from {biggest_impact[0]}")
    
    return results


def test_weight_balance_validation(client: httpx.Client) -> None:
    """Test scenario 5: Weight balance validation"""
    step("TEST SCENARIO 5: Weight balance validation")
    
    farmer, farmer_id, farm, farm_id = create_test_farmer(client, "BALANCE")
    trust_id, buyer_id, group_id = create_verifiers(client, farmer_id)
    
    # Test balanced vs unbalanced scenarios
    balance_cases = [
        ("Balanced Good", {"trust_rating": 3, "buyer_rating": 3, "group_cycles": 5}),
        ("Balanced Poor", {"trust_rating": 2, "buyer_rating": 2, "group_cycles": 2}),
        ("Unbalanced Good", {"trust_rating": 4, "buyer_rating": 2, "group_cycles": 2}),
        ("Unbalanced Poor", {"trust_rating": 1, "buyer_rating": 3, "group_cycles": 3}),
    ]
    
    results = {}
    for case_name, ratings in balance_cases:
        score = run_verification_session(client, farmer_id, **ratings)
        final_score = score['score_profile']['final_score']
        character_score = score['score_profile']['character_score']
        breakdown = score['score_profile'].get('character_breakdown', [])
        
        results[case_name] = {
            'final_score': final_score,
            'character_score': character_score,
            'breakdown': breakdown
        }
        
        print(f"{case_name}: Final={final_score}, Character={character_score}")
        
        # Print component breakdown
        for component in breakdown:
            print(f"  {component['component']}: {component['contribution']} (weight: {component['weight']})")
    
    # Analyze balance effects
    print("\nWeight Balance Analysis:")
    balanced_good = results["Balanced Good"]['final_score']
    unbalanced_good = results["Unbalanced Good"]['final_score']
    balanced_poor = results["Balanced Poor"]['final_score']
    unbalanced_poor = results["Unbalanced Poor"]['final_score']
    
    print(f"Balanced good score: {balanced_good}")
    print(f"Unbalanced good score: {unbalanced_good}")
    print(f"Balanced poor score: {balanced_poor}")
    print(f"Unbalanced poor score: {unbalanced_poor}")
    
    # Check if balanced scores are better than unbalanced for same overall level
    if balanced_good > unbalanced_good:
        print("✓ Balanced good scores better than unbalanced")
    else:
        print("✗ Balanced good scores not better than unbalanced")
    
    if balanced_poor > unbalanced_poor:
        print("✓ Balanced poor scores better than unbalanced")
    else:
        print("✗ Balanced poor scores not better than unbalanced")
    
    return results


def run(base_url: str) -> None:
    """Run all weight contribution tests"""
    with httpx.Client(base_url=base_url, timeout=60.0) as client:
        test_results = []
        
        # Test 1: Individual component contributions
        try:
            result1 = test_individual_component_contributions(client)
            test_results.append(("Individual Components", result1))
        except Exception as e:
            print(f"✗ Test 1 failed: {e}")
            test_results.append(("Individual Components", None))
        
        # Test 2: Weight sensitivity analysis
        try:
            result2 = test_weight_sensitivity_analysis(client)
            test_results.append(("Weight Sensitivity", result2))
        except Exception as e:
            print(f"✗ Test 2 failed: {e}")
            test_results.append(("Weight Sensitivity", None))
        
        # Test 3: Extreme weight scenarios
        try:
            result3 = test_extreme_weight_scenarios(client)
            test_results.append(("Extreme Scenarios", result3))
        except Exception as e:
            print(f"✗ Test 3 failed: {e}")
            test_results.append(("Extreme Scenarios", None))
        
        # Test 4: Component failure scenarios
        try:
            result4 = test_component_failure_scenarios(client)
            test_results.append(("Component Failure", result4))
        except Exception as e:
            print(f"✗ Test 4 failed: {e}")
            test_results.append(("Component Failure", None))
        
        # Test 5: Weight balance validation
        try:
            result5 = test_weight_balance_validation(client)
            test_results.append(("Weight Balance", result5))
        except Exception as e:
            print(f"✗ Test 5 failed: {e}")
            test_results.append(("Weight Balance", None))
        
        # Summary
        step("TEST SUMMARY")
        for test_name, result in test_results:
            if result:
                print(f"✓ {test_name}: Completed")
            else:
                print(f"✗ {test_name}: Failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()
    try:
        run(args.base_url)
    except httpx.HTTPStatusError as exc:
        print(f"\nFAILED at {exc.request.url}: {exc}", file=sys.stderr)
        sys.exit(1)