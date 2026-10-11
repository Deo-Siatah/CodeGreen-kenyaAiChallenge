"""
End-to-end smoke test for the Hifadhi scoring flow: create a farmer, a farm,
three verifiers (trust source, market actor, social group), link them, start
a verification session, submit all three responses, then fetch the score and
its explanation.

Run against a local dev server (uv run uvicorn main:app --reload), pointed at
your Neon TEST branch, never against main while you're iterating.

Usage:
    uv run python hifadhi_e2e_test.py
    uv run python hifadhi_e2e_test.py --base-url http://localhost:8000

ADJUST BEFORE FIRST RUN:
- The /respond payload shape below assumes ONE generic endpoint that accepts
  a discriminated union keyed by participant_type. If the agent instead built
  three separate typed endpoints for Section 13, update RESPOND_URL and the
  three payload builders (build_trust_response / build_buyer_response /
  build_group_response) to hit the right URLs instead.
- Field names in each create_* payload are a best guess based on the schemas
  discussed - check against the actual Pydantic request models if any of
  these 422 on first run, and fix the payload, not the server.
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


def run(base_url: str) -> None:
    with httpx.Client(base_url=base_url, timeout=60.0) as client:
        step("1. Create farmer")
        run_id = uuid.uuid4().hex[:10]
        farmer = post(client, "/api/farmers", {
            "full_name": "Test Farmer E2E",
            "national_id": f"E2E-{run_id}",
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
        print(f"farmer_id = {farmer_id}")

        step("2. Create farm")
        farm = post(client, f"/api/farmers/{farmer_id}/farm", {
            "acreage": 1.5,
            "production_type": "crop",
            "latitude": -1.1714,
            "longitude": 36.8356,  # Kiambu-area coordinates, real farmland
        })
        print(f"farm_id = {farm.get('id')}")

        step("3. Create a trust source (chief)")
        trust_source = post(client, "/api/trust/sources", {
            "name": "Test Chief",
            "category": "Chief",
            "phone": "+254700000002",
            "national_id": "88888888",
            "location": "Kiambu",
        })
        trust_source_id = trust_source["id"]

        step("4. Create a market actor (buyer)")
        market_actor = post(client, "/api/trust/market-actors", {
            "name": "Test Buyer Co",
            "actor_type": "Buyer",
            "phone": "+254700000003",
            "location": "Kiambu",
        })
        market_actor_id = market_actor["id"]

        step("5. Create a social group (Chama)")
        social_group = post(client, "/api/trust/social-groups", {
            "name": "Test Chama",
            "group_type": "Savings Group",
            "location": "Kiambu",
            "formation_year": 2019,
        })
        social_group_id = social_group["id"]

        step("6. Link all three to the farmer")
        post(client, f"/api/farmers/{farmer_id}/link-trust-source", {
            "related_id": trust_source_id,
        })
        post(client, f"/api/farmers/{farmer_id}/link-market-actor", {
            "related_id": market_actor_id,
        })
        post(client, f"/api/farmers/{farmer_id}/link-social-group", {
            "related_id": social_group_id,
        })

        step("7. Start verification session")
        session = post(client, "/api/verify/start", {"farmer_id": farmer_id})
        session_id = session["session_id"]
        status = get(client, f"/api/verify/{session_id}/status")
        participants = status["participants"]
        if len(participants) != 3:
            raise RuntimeError(f"Expected 3 participants, got {len(participants)}")
        print(f"session_id = {session_id}")
        for p in participants:
            print(f"  participant: {p['id']} type={p['participant_type']}")

        by_type = {p["participant_type"]: p["id"] for p in participants}

        step("8. Submit responses (trust_source, then market_actor, then social_group)")
        # NOTE: adjust payload shape/endpoint per the module docstring if the
        # agent built typed endpoints instead of one generic /respond route.
        result_trust = post(
            client,
            f"/api/verify/{session_id}/respond/{by_type['trust_source']}",
            {"participant_type": "trust_source", "rating": 4,
             "comments": "Known him for years, always reliable.",
             "personal_knowledge_flag": True},
        )
        print(f"session_status after 1st response: {result_trust.get('session_status')}")

        result_buyer = post(
            client,
            f"/api/verify/{session_id}/respond/{by_type['market_actor']}",
            {"participant_type": "market_actor", "reliability_rating": 4,
             "purchase_frequency": "weekly", "relationship_months": 24,
             "avg_volume_kg": 40},
        )
        print(f"session_status after 2nd response: {result_buyer.get('session_status')}")

        result_group = post(
            client,
            f"/api/verify/{session_id}/respond/{by_type['social_group']}",
            {"participant_type": "social_group", "consecutive_cycles": 5,
             "last_contribution_date": "2026-09-01", "contribution_amount": 500},
        )
        print(f"session_status after 3rd response: {result_group.get('session_status')}")
        print(f"score_result present: {result_group.get('score_result') is not None}")

        step("9. Fetch final result")
        score = get(client, f"/api/verify/{session_id}/result")
        score_profile = score["score_profile"]
        print(f"character_score = {score_profile.get('character_score')}")
        print(f"capacity_score  = {score_profile.get('capacity_score')}")
        print(f"final_score     = {score_profile.get('final_score')}")
        print(f"decision        = {score_profile.get('decision')}")
        print(f"amount          = {score_profile.get('recommended_amount')}")

        step("10. Fetch explanation")
        explanation = get(client, f"/api/verify/{session_id}/explanation?mode=farmer&language=English")
        print(explanation.get("explanation") or explanation)

        step("DONE — full flow completed without error")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()
    try:
        run(args.base_url)
    except httpx.HTTPStatusError as exc:
        print(f"\nFAILED at {exc.request.url}: {exc}", file=sys.stderr)
        sys.exit(1)