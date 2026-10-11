"""
Multiple-voucher pooling test (design doc 3.5) against the live API.

Keep this file NEXT TO test_defaulting_effects.py: it reuses that file's
check/step/scaled helpers.

How the expected numbers are derived
------------------------------------
Every farmer here has ONLY trust-source testimony (no buyer, no Chama, no
settlement). The character score renormalises over the components that exist,
so with a single component it equals the pooled testimony score exactly:

    pooled = sum(category_weight * scaled_rating) / sum(category_weight)
    if the pool holds 3 or more DISTINCT categories: pooled = min(100, pooled * 1.1)

Verifiers are brand new, so credibility is 1.0 and drops out. No farm is
created, so there is no capacity axis and final_score == character_score; the
assertions use character_score either way.

Each case gets its OWN farmer. Testimony from every session counts toward a
farmer's score, so reusing one farmer would mix earlier cases into later ones.

Usage:
    uv run python test_multiple_vouchers.py --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

import httpx

from test_defaulting_effects import CHECKS, TOLERANCE, check, digits, scaled, step

DEFAULT_BASE_URL = "http://localhost:8000"

# Cold-start category weights, mirrored from services/weighting.py.
BASE_WEIGHT = {
    "Chief": 4.0,
    "Village Elder": 3.0,
    "Teacher": 3.0,
    "Religious Leader": 3.0,
    "Neighbor": 1.0,
}
DIVERSITY_MIN_CATEGORIES = 3
DIVERSITY_BONUS = 1.1

Member = tuple[str, int]  # (category, rating)


def expected_pool(members: list[Member]) -> float:
    total_weight = sum(BASE_WEIGHT[category] for category, _ in members)
    pooled = sum(BASE_WEIGHT[category] * scaled(rating) for category, rating in members) / total_weight
    if len({category for category, _ in members}) >= DIVERSITY_MIN_CATEGORIES:
        pooled = min(100.0, pooled * DIVERSITY_BONUS)
    return pooled


# --------------------------------------------------------------------------
# quiet API helpers (one summary line per case instead of 15 request lines)
# --------------------------------------------------------------------------
def api(client: httpx.Client, method: str, path: str, **kwargs: Any) -> Any:
    response = client.request(method, path, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(f"{method} {path} -> {response.status_code}: {response.text[:300]}")
    return response.json()


def new_farmer(client: httpx.Client, label: str) -> str:
    return api(client, "POST", "/api/farmers", json={
        "full_name": f"Voucher Test {label} {digits(5)}",
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
    })["id"]


def add_source(client: httpx.Client, farmer_id: str, category: str) -> str:
    """Create a trust source of `category` and link it to the farmer."""
    payload = {
        "name": f"{category} {digits(5)}",
        "category": category,
        "phone": f"+2547{digits(8)}",
        "national_id": digits(8),
        "location": "Kiambu",
    }
    response = client.post("/api/trust/sources", json=payload)
    if response.status_code == 422:  # the name field has differed between schemas
        payload["full_name"] = payload.pop("name")
        response = client.post("/api/trust/sources", json=payload)
    if response.status_code >= 400:
        raise RuntimeError(f"POST /api/trust/sources -> {response.status_code}: {response.text[:300]}")
    source_id = response.json()["id"]
    api(client, "POST", f"/api/farmers/{farmer_id}/link-trust-source", json={"related_id": source_id})
    return source_id


def trust(rating: int) -> dict[str, Any]:
    return {
        "participant_type": "trust_source",
        "rating": rating,
        "comments": "voucher test",
        "personal_knowledge_flag": True,
    }


def verify(client: httpx.Client, farmer_id: str, ratings: list[tuple[str, int]]) -> float:
    """One verification session; ratings = [(source_id, rating), ...]. Returns character_score."""
    sid = api(client, "POST", "/api/verify/start", json={"farmer_id": farmer_id})["session_id"]
    participants = api(client, "GET", f"/api/verify/{sid}/status")["participants"]
    by_source = {p["participant_id"]: p["id"] for p in participants}
    for source_id, rating in ratings:
        api(client, "POST", f"/api/verify/{sid}/respond/{by_source[source_id]}", json=trust(rating))
    score = api(client, "GET", f"/api/verify/{sid}/result")["score_profile"]
    return float(score["character_score"])


def run_case(client: httpx.Client, label: str, members: list[Member]) -> float:
    farmer_id = new_farmer(client, label)
    ratings = [(add_source(client, farmer_id, category), rating) for category, rating in members]
    return verify(client, farmer_id, ratings)


def expect_pool(client: httpx.Client, name: str, members: list[Member]) -> None:
    want = expected_pool(members)
    try:
        got = run_case(client, name[:20], members)
    except Exception as exc:  # one broken case must not hide the rest
        check(name, False, f"{type(exc).__name__}: {exc}")
        return
    check(f"{name} -> {want:.2f}", abs(got - want) <= TOLERANCE, f"got {got:.2f}")


# --------------------------------------------------------------------------
# cases
# --------------------------------------------------------------------------
def neighbours(*ratings: int) -> list[Member]:
    return [("Neighbor", rating) for rating in ratings]


GROUPS: list[tuple[str, list[tuple[str, list[Member]]]]] = [
    ("A. Same category (no bonus): the result is the plain average", [
        ("3 neighbours, all excellent", neighbours(4, 4, 4)),
        ("3 neighbours, all poor", neighbours(1, 1, 1)),
        ("3 neighbours, mixed 4/2/3", neighbours(4, 2, 3)),
        ("3 neighbours, one dissenter 4/1/1", neighbours(4, 1, 1)),
    ]),
    ("B. Headcount alone must not inflate a score (unanimous 'above average')", [
        ("3 neighbours all 3", neighbours(*[3] * 3)),
        ("4 neighbours all 3", neighbours(*[3] * 4)),
        ("6 neighbours all 3", neighbours(*[3] * 6)),
        ("10 neighbours all 3", neighbours(*[3] * 10)),
    ]),
    ("C. One dissenter among many dilutes as the group grows", [
        ("4 neighbours, one dissenter", neighbours(4, 4, 4, 1)),
        ("6 neighbours, one dissenter", neighbours(4, 4, 4, 4, 4, 1)),
    ]),
    ("D. Polarised groups", [
        ("6 neighbours split 3-3", neighbours(4, 4, 4, 1, 1, 1)),
        ("6 neighbours, one against five", neighbours(4, 1, 1, 1, 1, 1)),
        ("6 neighbours split 2-4", neighbours(4, 4, 1, 1, 1, 1)),
    ]),
    ("E. Category weight: a Chief counts four times a Neighbour", [
        ("Chief excellent, Neighbour poor", [("Chief", 4), ("Neighbor", 1)]),
        ("Chief poor, Neighbour excellent", [("Chief", 1), ("Neighbor", 4)]),
    ]),
    ("F. Diversity bonus: 3+ distinct categories earn x1.1, once, capped at 100", [
        ("3 neighbours all 3 (no bonus)", neighbours(3, 3, 3)),
        ("Chief + Elder + Teacher all 3 (bonus)",
         [("Chief", 3), ("Village Elder", 3), ("Teacher", 3)]),
        ("Chief + Elder + Teacher all 4 (bonus capped at 100)",
         [("Chief", 4), ("Village Elder", 4), ("Teacher", 4)]),
        ("Chief + Elder + Teacher rated 4/2/2 (bonus on a weighted average)",
         [("Chief", 4), ("Village Elder", 2), ("Teacher", 2)]),
        ("Two categories only, Chief + Chief + Neighbour (no bonus)",
         [("Chief", 3), ("Chief", 3), ("Neighbor", 3)]),
        ("Four categories all 3 (bonus applied once, not per category)",
         [("Chief", 3), ("Village Elder", 3), ("Teacher", 3), ("Religious Leader", 3)]),
    ]),
]


def probe_accumulation(client: httpx.Client) -> None:
    step("Probe: does a second verification replace the first or add to it? (informational)")
    farmer_id = new_farmer(client, "ACCUM")
    sources = [add_source(client, farmer_id, "Neighbor") for _ in range(3)]
    first = verify(client, farmer_id, [(s, 4) for s in sources])
    second = verify(client, farmer_id, [(s, 1) for s in sources])
    print(f"round 1 (all excellent): character = {first:.2f}")
    print(f"round 2 (all poor)     : character = {second:.2f}")
    if abs(second - 50.0) <= TOLERANCE:
        print("INFO: ACCUMULATES. Round 2 was averaged with round 1, so old testimony counts "
              "forever. Decide whether testimony should expire or be down-weighted with age.")
    elif abs(second - 0.0) <= TOLERANCE:
        print("INFO: REPLACES. Only the latest round counts.")
    else:
        print("INFO: UNEXPECTED combination; look at how signals are gathered per farmer.")


def run(base_url: str) -> int:
    with httpx.Client(base_url=base_url, timeout=120.0) as client:
        for title, cases in GROUPS:
            step(title)
            for name, members in cases:
                expect_pool(client, name, members)

    with httpx.Client(base_url=base_url, timeout=120.0) as client:
        try:
            probe_accumulation(client)
        except Exception as exc:
            print(f"INFO: accumulation probe crashed: {type(exc).__name__}: {exc}")

    step("SUMMARY")
    failed = [c for c in CHECKS if not c[1]]
    print(f"{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    for name, _, detail in failed:
        print(f"  FAILED: {name}" + (f" - {detail}" if detail else ""))
    print("\nNOT TESTED: disagreement tracking (design doc 3.5, 'testimony_agreement'). "
          "scoring_service builds no such component and no route exposes score components.")
    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    sys.exit(run(parser.parse_args().base_url))