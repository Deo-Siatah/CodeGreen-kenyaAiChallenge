"""
Simple test script to verify basic API functionality before running edge case tests.

This script tests the basic API endpoints to ensure they're working correctly
before running the more complex edge case tests.

Run: uv run python test_basic_api.py --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import sys
import uuid
from typing import Any
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


def test_basic_endpoints(client: httpx.Client) -> None:
    """Test basic API endpoints"""
    step("Testing Basic API Endpoints")
    
    # Test 1: Create farmer
    run_id = uuid.uuid4().hex[:10]
    farmer = post(client, "/api/farmers", {
        "full_name": "Basic Test Farmer",
        "national_id": f"BASIC-{run_id}",
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
    print(f"✓ Farmer created: {farmer_id}")
    
    # Test 2: Create farm
    farm = post(client, f"/api/farmers/{farmer_id}/farm", {
        "acreage": 1.5,
        "production_type": "crop",
        "latitude": -1.1714,
        "longitude": 36.8356,
    })
    farm_id = farm["id"]
    print(f"✓ Farm created: {farm_id}")
    
    # Test 3: Create trust source
    trust_source = post(client, "/api/trust/sources", {
        "name": "Test Chief Basic",
        "category": "Chief",
        "phone": "+254700000002",
        "national_id": "88888888",
        "location": "Kiambu",
    })
    trust_source_id = trust_source["id"]
    print(f"✓ Trust source created: {trust_source_id}")
    
    # Test 4: Link trust source to farmer
    post(client, f"/api/farmers/{farmer_id}/link-trust-source", {
        "related_id": trust_source_id,
    })
    print("✓ Trust source linked to farmer")
    
    # Test 5: Start verification session
    session = post(client, "/api/verify/start", {"farmer_id": farmer_id})
    session_id = session["session_id"]
    print(f"✓ Verification session started: {session_id}")
    
    # Test 6: Get session status
    status = get(client, f"/api/verify/{session_id}/status")
    participants = status["participants"]
    print(f"✓ Session status retrieved: {len(participants)} participants")
    
    # Test 7: Submit trust source response
    trust_participant = next((p for p in participants if p["participant_type"] == "trust_source"), None)
    if trust_participant:
        post(client, f"/api/verify/{session_id}/respond/{trust_participant['id']}", {
            "participant_type": "trust_source", "rating": 4,
            "comments": "Test response", "personal_knowledge_flag": True,
        })
        print("✓ Trust source response submitted")
    
    # Test 8: Get score result
    score = get(client, f"/api/verify/{session_id}/result")
    final_score = score["score_profile"]["final_score"]
    print(f"✓ Score retrieved: {final_score}")
    
    # Test 9: Get explanation
    explanation = get(client, f"/api/verify/{session_id}/explanation?mode=farmer&language=English")
    print("✓ Explanation retrieved")
    
    print("\n✅ All basic API endpoints working correctly!")
    return True


def test_error_handling(client: httpx.Client) -> None:
    """Test error handling for invalid requests"""
    step("Testing Error Handling")
    
    try:
        # Test invalid farmer ID
        get(client, "/api/verify/invalid-session-id/status")
        print("✗ Should have failed for invalid session ID")
        return False
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            print("✓ Correctly handled invalid session ID")
        else:
            print(f"✗ Unexpected error for invalid session ID: {e}")
            return False
    
    try:
        # Test invalid response payload
        run_id = uuid.uuid4().hex[:10]
        farmer = post(client, "/api/farmers", {
            "full_name": "Error Test Farmer",
            "national_id": f"ERROR-{run_id}",
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
        
        session = post(client, "/api/verify/start", {"farmer_id": farmer_id})
        session_id = session["session_id"]
        
        # Try to submit invalid response
        post(client, f"/api/verify/{session_id}/respond/invalid-id", {
            "participant_type": "trust_source", "rating": 5,  # Invalid rating
            "comments": "Test response", "personal_knowledge_flag": True,
        })
        print("✗ Should have failed for invalid rating")
        return False
    except httpx.HTTPStatusError as e:
        if e.response.status_code in [422, 404]:
            print("✓ Correctly handled invalid response")
        else:
            print(f"✗ Unexpected error for invalid response: {e}")
            return False
    
    print("✅ Error handling working correctly!")
    return True


def run(base_url: str) -> None:
    """Run basic API tests"""
    with httpx.Client(base_url=base_url, timeout=60.0) as client:
        try:
            # Test basic endpoints
            basic_result = test_basic_endpoints(client)
            
            # Test error handling
            error_result = test_error_handling(client)
            
            if basic_result and error_result:
                print("\n🎉 All basic API tests passed!")
                print("You can now run the edge case test scripts.")
            else:
                print("\n❌ Some basic API tests failed.")
                print("Fix the API issues before running edge case tests.")
                
        except Exception as e:
            print(f"\n❌ Basic API tests failed with error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()
    try:
        run(args.base_url)
    except httpx.HTTPStatusError as exc:
        print(f"\nFAILED at {exc.request.url}: {exc}", file=sys.stderr)
        sys.exit(1)