"""
Attribute-invariance test against the live API.

The claim being tested: the same evidence produces the same outcome whoever the
farmer is. Every farmer here receives IDENTICAL verification evidence (a Chief
rating 3, a Buyer rating 3, a Chama with 4 cycles) and the SAME farm
coordinates. Only one attribute changes per variant. The character score, the
capacity score, the final score, the decision and the recommended amount must
all match a baseline farmer.

Variants cover gender, age, name (ethnicity proxy), region text, farming type,
years farming and acreage. Region varies the TEXT only: the farm coordinates
stay fixed, because different land legitimately gives a different satellite
reading and that is not what is being tested here. A "baseline repeat" control
runs first so any satellite drift or rounding noise shows up as a control
failure rather than as a false fairness failure.

Keep this file NEXT TO test_defaulting_effects.py and test_multiple_vouchers.py;
it reuses their helpers. Each farm creation calls Earth Engine, so allow a couple
of minutes.

Writes fairness_results.csv (one row per variant) for charts.

Usage:
    uv run python test_fairness_invariance.py --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, timedelta
from typing import Any

import httpx

from test_defaulting_effects import CHECKS, check, digits, step
from test_multiple_vouchers import add_source, api, trust

DEFAULT_BASE_URL = "http://localhost:8000"
ATTR_TOLERANCE = 0.01
FIELDS = ("character_score", "capacity_score", "final_score", "decision", "recommended_amount")

BASE_FARMER: dict[str, Any] = {
    "full_name": "Wanjiku Kamau",
    "gender": "female",
    "date_of_birth": "1985-04-12",
    "location": "Kiambu",
    "village": "Test Village",
    "sub_county": "Test Sub-County",
    "county": "Kiambu",
    "farming_type": "mixed",
    "years_farming": 6,
}
BASE_FARM: dict[str, Any] = {
    "acreage": 1.5,
    "production_type": "crop",
    "latitude": -1.1714,
    "longitude": 36.8356,
}

# (attribute, value label, farmer overrides, farm overrides)
VARIANTS: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = [
    ("control", "baseline repeat", {}, {}),
    ("gender", "male", {"gender": "male"}, {}),
    ("age", "born 1960", {"date_of_birth": "1960-01-01"}, {}),
    ("age", "born 2004 (youth)", {"date_of_birth": "2004-06-01"}, {}),
    ("name", "Luo name", {"full_name": "Otieno Odhiambo"}, {}),
    ("name", "Kalenjin name", {"full_name": "Kipchoge Kiprop"}, {}),
    ("name", "Somali name", {"full_name": "Abdi Hassan Mohamed"}, {}),
    ("region", "Turkana (text only)", {
        "location": "Turkana", "county": "Turkana",
        "village": "Lodwar", "sub_county": "Turkana Central"}, {}),
    ("region", "Kisumu (text only)", {
        "location": "Kisumu", "county": "Kisumu",
        "village": "Nyalenda", "sub_county": "Kisumu East"}, {}),
    ("farming_type", "livestock", {"farming_type": "livestock"}, {}),
    ("years_farming", "1 year", {"years_farming": 1}, {}),
    ("years_farming", "30 years", {"years_farming": 30}, {}),
    ("acreage", "0.25 acres", {}, {"acreage": 0.25}),
    ("acreage", "12 acres", {}, {"acreage": 12.0}),
]

SKIPPED: list[tuple[str, str]] = []


def farmer_body(overrides: dict[str, Any]) -> dict[str, Any]:
    body = {**BASE_FARMER, "national_id": digits(8), "phone": f"+2547{digits(8)}"}
    body.update(overrides)
    return body


def evaluate(client: httpx.Client, farmer_over: dict[str, Any], farm_over: dict[str, Any]) -> dict[str, Any]:
    """Run the identical evidence for one farmer and return the outcome fields."""
    farmer_id = api(client, "POST", "/api/farmers", json=farmer_body(farmer_over))["id"]
    api(client, "POST", f"/api/farmers/{farmer_id}/farm", json={**BASE_FARM, **farm_over})

    add_source(client, farmer_id, "Chief")
    buyer_id = api(client, "POST", "/api/trust/market-actors", json={
        "name": f"Buyer {digits(4)}", "actor_type": "Buyer",
        "phone": f"+2547{digits(8)}", "location": "Kiambu"})["id"]
    api(client, "POST", f"/api/farmers/{farmer_id}/link-market-actor", json={"related_id": buyer_id})
    group_id = api(client, "POST", "/api/trust/social-groups", json={
        "name": f"Chama {digits(4)}", "group_type": "Savings Group",
        "location": "Kiambu", "formation_year": 2019})["id"]
    api(client, "POST", f"/api/farmers/{farmer_id}/link-social-group", json={"related_id": group_id})

    sid = api(client, "POST", "/api/verify/start", json={"farmer_id": farmer_id})["session_id"]
    parts = {p["participant_type"]: p["id"] for p in
             api(client, "GET", f"/api/verify/{sid}/status")["participants"]}

    api(client, "POST", f"/api/verify/{sid}/respond/{parts['trust_source']}", json=trust(3))
    api(client, "POST", f"/api/verify/{sid}/respond/{parts['market_actor']}", json={
        "participant_type": "market_actor", "reliability_rating": 3,
        "purchase_frequency": "weekly", "relationship_months": 24, "avg_volume_kg": 40})
    api(client, "POST", f"/api/verify/{sid}/respond/{parts['social_group']}", json={
        "participant_type": "social_group", "consecutive_cycles": 4,
        "last_contribution_date": (date.today() - timedelta(days=10)).isoformat(),
        "contribution_amount": 500})

    profile = api(client, "GET", f"/api/verify/{sid}/result")["score_profile"]
    return {field: profile.get(field) for field in FIELDS}


def same(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= ATTR_TOLERANCE
    return a == b


def run_variant(
    client: httpx.Client,
    baseline: dict[str, Any],
    variant: tuple[str, str, dict[str, Any], dict[str, Any]],
    rows: list[dict[str, Any]],
    deviations: list[float],
) -> None:
    attribute, value, farmer_over, farm_over = variant
    name = f"{attribute} = {value}"
    try:
        result = evaluate(client, farmer_over, farm_over)
    except RuntimeError as exc:
        if "-> 422" in str(exc):
            SKIPPED.append((name, str(exc)[:160]))
            print(f"  [SKIP] {name} - the schema rejected this value")
            return
        check(f"{name}: ran to completion", False, str(exc)[:200])
        return

    diffs = [f"{f}: {baseline[f]} -> {result[f]}" for f in FIELDS if not same(baseline[f], result[f])]
    check(f"{name}: identical to baseline", not diffs, "; ".join(diffs))

    for field in ("character_score", "capacity_score", "final_score"):
        if baseline[field] is not None and result[field] is not None:
            deviations.append(abs(float(result[field]) - float(baseline[field])))
    rows.append({"attribute": attribute, "value": value, **result, "matches_baseline": not diffs})


def write_csv(path: str, baseline: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    columns = ["attribute", "value", *FIELDS, "matches_baseline"]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerow({"attribute": "baseline", "value": "reference", **baseline, "matches_baseline": True})
        writer.writerows(rows)
    print(f"\nWrote {path} ({len(rows) + 1} rows)")


def run(base_url: str, csv_path: str) -> int:
    rows: list[dict[str, Any]] = []
    deviations: list[float] = []
    with httpx.Client(base_url=base_url, timeout=180.0) as client:
        step("Baseline")
        try:
            baseline = evaluate(client, {}, {})
        except Exception as exc:
            print(f"Baseline farmer could not be scored: {type(exc).__name__}: {exc}")
            return 1
        print("baseline:", baseline)

        step("Same evidence, one attribute changed at a time")
        for variant in VARIANTS:
            run_variant(client, baseline, variant, rows, deviations)

    write_csv(csv_path, baseline, rows)

    step("SUMMARY")
    failed = [c for c in CHECKS if not c[1]]
    print(f"{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    if deviations:
        print(f"Largest score deviation from baseline across {len(deviations)} comparisons: "
              f"{max(deviations):.3f} points")
    for name, reason in SKIPPED:
        print(f"  SKIPPED: {name} ({reason})")
    for name, _, detail in failed:
        print(f"  FAILED: {name}" + (f" - {detail}" if detail else ""))
    print("\nNOT VISIBLE TO THIS TEST: bias in how the satellite reading is measured for small "
          "plots, and bias in who has access to many kinds of verifier. See the pytest design "
          "findings and the empirical audit once real farms exist.")
    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--csv", default="fairness_results.csv")
    args = parser.parse_args()
    sys.exit(run(args.base_url, args.csv))