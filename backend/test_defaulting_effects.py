"""
Loan guard / default / repayment feedback test for Hifadhi.

Run this AFTER the loan-flow fix (a loan is linked to the score profile that
approved it, and the amount is capped by the STORED recommendation, not a
client-supplied one).

Routes used (all exist today):
  POST /api/farmers, /api/farmers/{id}/farm
  POST /api/trust/sources | market-actors | social-groups
  POST /api/farmers/{id}/link-trust-source | link-market-actor | link-social-group
       body: {"related_id": "<uuid>"}
  POST /api/verify/start, /api/verify/{sid}/respond/{pid}
  GET  /api/verify/{sid}/status, /api/verify/{sid}/result
  POST /api/loans, /api/loans/{id}/disburse | repay | default
  
Unlike a print-and-eyeball script, this asserts exact numbers. With one
trust-source testimony and one buyer testimony of equal rating, each pool
reduces to credibility * scaled_rating (the category weight cancels), so the
character score moves by a predictable amount:

    delta = (0.15 + 0.30) * scaled_rating * (credibility - 1) / (0.15 + 0.30 + 0.35)

where credibility = 1 + 0.5 * (repaid - defaulted) / (repaid + defaulted + 5).
The discipline signal is identical before and after, so it drops out of the
delta. Settlement is absent, so the available weights are testimony, buyer and
discipline only.

Ratings of 4 are used for default scenarios (credibility can only fall, so the
100-point ceiling never interferes). Ratings of 3 are used for the repayment
scenario so a rising credibility has headroom below 100.

Usage:
    uv run python test_defaulting_effects.py --base-url http://localhost:8000

Exit code is 0 only if every check passes.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import date, timedelta
from typing import Any

import httpx

DEFAULT_BASE_URL = "http://localhost:8000"
TOLERANCE = 0.05  # scores are stored rounded; two rounded values differ by <0.01

TESTIMONY_W, BUYER_W, DISCIPLINE_W = 0.15, 0.30, 0.35
AVAILABLE_W = TESTIMONY_W + BUYER_W + DISCIPLINE_W

CHECKS: list[tuple[str, bool, str]] = []


# --------------------------------------------------------------------------
# expected-value maths (mirrors credibility_repository / weighting)
# --------------------------------------------------------------------------
def credibility(repaid: int, defaulted: int) -> float:
    return 1.0 + 0.5 * (repaid - defaulted) / (repaid + defaulted + 5)


def scaled(rating: int) -> float:
    return (rating - 1) / 3 * 100


def expected_character_delta(rating: int, repaid: int, defaulted: int) -> float:
    return (
        (TESTIMONY_W + BUYER_W)
        * scaled(rating)
        * (credibility(repaid, defaulted) - 1.0)
        / AVAILABLE_W
    )


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def step(label: str) -> None:
    print(f"\n{'=' * 60}\n{label}\n{'=' * 60}")


def check(name: str, passed: bool, detail: str = "") -> None:
    CHECKS.append((name, passed, detail))
    suffix = f" - {detail}" if detail else ""
    print(f"  [{'PASS' if passed else 'FAIL'}] {name}{suffix}")


def call(client: httpx.Client, method: str, path: str, **kwargs: Any) -> httpx.Response:
    response = client.request(method, path, **kwargs)
    print(f"{method} {path} -> {response.status_code}")
    return response


def ok(client: httpx.Client, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    response = call(client, method, path, **kwargs)
    if response.status_code >= 400:
        print(response.text)
        response.raise_for_status()
    return response.json()


def digits(n: int) -> str:
    return str(uuid.uuid4().int)[:n]


# --------------------------------------------------------------------------
# setup + verification
# --------------------------------------------------------------------------
def create_farmer_with_verifiers(client: httpx.Client, label: str) -> str:
    farmer = ok(client, "POST", "/api/farmers", json={
        "full_name": f"Loan Test {label}",
        "national_id": digits(8),
        "phone": f"+2547{digits(8)}",
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

    ok(client, "POST", f"/api/farmers/{farmer_id}/farm", json={
        "acreage": 1.5,
        "production_type": "crop",
        "latitude": -1.1714,
        "longitude": 36.8356,
    })

    # The trust-source name field has differed between scripts ("name" vs
    # "full_name"); try one, fall back to the other on a validation error.
    source_payload = {
        "name": f"Chief {label}",
        "category": "Chief",
        "phone": f"+2547{digits(8)}",
        "national_id": digits(8),
        "location": "Kiambu",
    }
    response = call(client, "POST", "/api/trust/sources", json=source_payload)
    if response.status_code == 422:
        source_payload["full_name"] = source_payload.pop("name")
        response = call(client, "POST", "/api/trust/sources", json=source_payload)
    response.raise_for_status()
    trust_source_id = response.json()["id"]

    market_actor_id = ok(client, "POST", "/api/trust/market-actors", json={
        "name": f"Buyer {label}",
        "actor_type": "Buyer",
        "phone": f"+2547{digits(8)}",
        "location": "Kiambu",
    })["id"]

    social_group_id = ok(client, "POST", "/api/trust/social-groups", json={
        "name": f"Chama {label}",
        "group_type": "Savings Group",
        "location": "Kiambu",
        "formation_year": 2019,
    })["id"]

    for kind, related_id in (
        ("link-trust-source", trust_source_id),
        ("link-market-actor", market_actor_id),
        ("link-social-group", social_group_id),
    ):
        ok(client, "POST", f"/api/farmers/{farmer_id}/{kind}", json={"related_id": related_id})

    return farmer_id


def verify_round(
    client: httpx.Client, farmer_id: str, trust_rating: int, buyer_rating: int, cycles: int
) -> dict[str, Any]:
    """Run one full verification session and return the score profile."""
    session = ok(client, "POST", "/api/verify/start", json={"farmer_id": farmer_id})
    sid = session["session_id"]
    participants = ok(client, "GET", f"/api/verify/{sid}/status")["participants"]
    by_type = {p["participant_type"]: p["id"] for p in participants}

    ok(client, "POST", f"/api/verify/{sid}/respond/{by_type['trust_source']}", json={
        "participant_type": "trust_source",
        "rating": trust_rating,
        "comments": "loan test",
        "personal_knowledge_flag": True,
    })
    ok(client, "POST", f"/api/verify/{sid}/respond/{by_type['market_actor']}", json={
        "participant_type": "market_actor",
        "reliability_rating": buyer_rating,
        "purchase_frequency": "weekly",
        "relationship_months": 24,
        "avg_volume_kg": 40,
    })
    ok(client, "POST", f"/api/verify/{sid}/respond/{by_type['social_group']}", json={
        "participant_type": "social_group",
        "consecutive_cycles": cycles,
        "last_contribution_date": (date.today() - timedelta(days=10)).isoformat(),
        "contribution_amount": 500,
    })

    return ok(client, "GET", f"/api/verify/{sid}/result")["score_profile"]


def recommended(profile: dict[str, Any]) -> float:
    amount = profile.get("recommended_amount")
    if amount is None:
        raise RuntimeError(
            f"Farmer is not loan-eligible at these ratings (decision="
            f"{profile.get('decision')}, final_score={profile.get('final_score')}); "
            "raise the ratings in the scenario."
        )
    return float(amount)


def take_loan(client: httpx.Client, farmer_id: str, amount: float) -> dict[str, Any]:
    return ok(client, "POST", "/api/loans", json={
        "farmer_id": farmer_id,
        "amount": amount,
        "purpose": "farming_inputs",
        "duration_months": 6,
        "interest_rate": 10.0,
    })


# --------------------------------------------------------------------------
# scenarios
# --------------------------------------------------------------------------
def scenario_guards(client: httpx.Client) -> None:
    step("SCENARIO 1: loan guards and state machine")
    farmer_id = create_farmer_with_verifiers(client, "GUARD")
    profile = verify_round(client, farmer_id, trust_rating=4, buyer_rating=4, cycles=5)
    limit = recommended(profile)
    print(f"recommended_amount = {limit}")

    over = call(client, "POST", "/api/loans", json={
        "farmer_id": farmer_id, "amount": limit + 1, "purpose": "farming_inputs",
        "duration_months": 6, "interest_rate": 10.0,
    })
    check("loan above the stored recommendation is rejected with a 4xx",
          400 <= over.status_code < 500, f"got {over.status_code}")

    loan = take_loan(client, farmer_id, min(500.0, limit))
    check("loan is linked to the score profile that approved it",
          str(loan.get("score_profile_id")) == str(profile["id"]),
          f"loan.score_profile_id={loan.get('score_profile_id')} score.id={profile['id']}")

    early = call(client, "POST", f"/api/loans/{loan['id']}/default")
    check("defaulting a loan that was never disbursed returns 4xx, not 500",
          400 <= early.status_code < 500, f"got {early.status_code}")

    ok(client, "POST", f"/api/loans/{loan['id']}/disburse")
    twice = call(client, "POST", f"/api/loans/{loan['id']}/disburse")
    check("disbursing the same loan twice returns 4xx, not 500",
          400 <= twice.status_code < 500, f"got {twice.status_code}")


def scenario_default_feedback(client: httpx.Client) -> None:
    step("SCENARIO 2: defaults lower the next score by the predicted amount")
    farmer_id = create_farmer_with_verifiers(client, "DEFAULT")
    rating = 4

    score1 = verify_round(client, farmer_id, rating, rating, cycles=5)
    char1 = float(score1["character_score"])

    loan1 = take_loan(client, farmer_id, min(500.0, recommended(score1)))
    ok(client, "POST", f"/api/loans/{loan1['id']}/disburse")
    ok(client, "POST", f"/api/loans/{loan1['id']}/default")

    score2 = verify_round(client, farmer_id, rating, rating, cycles=5)
    char2 = float(score2["character_score"])
    want = expected_character_delta(rating, repaid=0, defaulted=1)
    got = char2 - char1
    check("one default lowers the character score by the predicted amount",
          abs(got - want) <= TOLERANCE,
          f"expected {want:+.3f}, got {got:+.3f} ({char1} -> {char2})")

    loan2 = take_loan(client, farmer_id, min(500.0, recommended(score2)))
    ok(client, "POST", f"/api/loans/{loan2['id']}/disburse")
    ok(client, "POST", f"/api/loans/{loan2['id']}/default")

    score3 = verify_round(client, farmer_id, rating, rating, cycles=5)
    char3 = float(score3["character_score"])
    want_total = expected_character_delta(rating, repaid=0, defaulted=2)
    got_total = char3 - char1
    check("two defaults compound to the predicted total",
          abs(got_total - want_total) <= TOLERANCE,
          f"expected {want_total:+.3f}, got {got_total:+.3f} ({char1} -> {char3})")
    check("second default hurts more than the first, but by a shrinking step",
          char3 < char2 < char1, f"{char1} > {char2} > {char3}")


def scenario_repay_feedback(client: httpx.Client) -> None:
    step("SCENARIO 3: repayment raises the next score by the predicted amount")
    farmer_id = create_farmer_with_verifiers(client, "REPAY")
    rating = 3  # headroom below the 100 ceiling so a rise is visible

    score1 = verify_round(client, farmer_id, rating, rating, cycles=6)
    char1 = float(score1["character_score"])

    loan = take_loan(client, farmer_id, min(500.0, recommended(score1)))
    ok(client, "POST", f"/api/loans/{loan['id']}/disburse")
    ok(client, "POST", f"/api/loans/{loan['id']}/repay")

    score2 = verify_round(client, farmer_id, rating, rating, cycles=6)
    char2 = float(score2["character_score"])
    want = expected_character_delta(rating, repaid=1, defaulted=0)
    got = char2 - char1
    check("one repayment raises the character score by the predicted amount",
          abs(got - want) <= TOLERANCE,
          f"expected {want:+.3f}, got {got:+.3f} ({char1} -> {char2})")
    check("repayment stays within the 0-100 scale",
          0.0 <= char2 <= 100.0 and 0.0 <= float(score2["final_score"]) <= 100.0,
          f"character={char2} final={score2['final_score']}")


# --------------------------------------------------------------------------
def run(base_url: str) -> int:
    with httpx.Client(base_url=base_url, timeout=120.0) as client:
        for scenario in (scenario_guards, scenario_default_feedback, scenario_repay_feedback):
            try:
                scenario(client)
            except Exception as exc:  # a crashed scenario is a failed check, not a skipped one
                check(f"{scenario.__name__} ran to completion", False, f"{type(exc).__name__}: {exc}")

    step("SUMMARY")
    failed = [c for c in CHECKS if not c[1]]
    print(f"{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    for name, _, detail in failed:
        print(f"  FAILED: {name}" + (f" - {detail}" if detail else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    sys.exit(run(parser.parse_args().base_url))