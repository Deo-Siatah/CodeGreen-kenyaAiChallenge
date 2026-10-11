"""
Edge-case battery for the Hifadhi API.

Keep this file NEXT TO test_defaulting_effects.py: it reuses that file's
helpers (create_farmer_with_verifiers, verify_round, take_loan, ...).

The contract being tested is simple:
  * input the API should refuse  -> a 4xx, never a 5xx and never a 2xx
  * two requests racing for one resource -> exactly one wins
  * a long clean record -> scores stay inside 0-100

A FAIL here is a finding, not a broken test. If the first check inside a
battery fails by returning 2xx, later steps in that battery may fail as a
consequence (the illegal request consumed state); fix the first failure first.

Batteries
  A  bad input and unknown ids
  B  illegal verification responses
  C  nobody answers (no signals at all)
  D  a verifier who does not know the farmer
  E  races: double response, simultaneous completion, double disburse/default
  F  the 100-point ceiling after a clean repayment record
  G  policy probe (informational only, no pass/fail)

Usage:
    uv run python test_edge_cases.py --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from typing import Any

import httpx

from test_defaulting_effects import (
    BUYER_W,
    CHECKS,
    DISCIPLINE_W,
    TOLERANCE,
    call,
    check,
    create_farmer_with_verifiers,
    digits,
    ok,
    recommended,
    scaled,
    step,
    take_loan,
    verify_round,
)

DEFAULT_BASE_URL = "http://localhost:8000"
CEILING_ROUNDS = 4


# --------------------------------------------------------------------------
# payload builders
# --------------------------------------------------------------------------
def farmer_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "full_name": f"Edge Case {digits(6)}",
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
    }
    payload.update(overrides)
    return payload


def farm_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "acreage": 1.5,
        "production_type": "crop",
        "latitude": -1.1714,
        "longitude": 36.8356,
    }
    payload.update(overrides)
    return payload


def trust(rating: int = 4, known: bool = True) -> dict[str, Any]:
    return {
        "participant_type": "trust_source",
        "rating": rating,
        "comments": "edge case",
        "personal_knowledge_flag": known,
    }


def buyer(rating: int = 4) -> dict[str, Any]:
    return {
        "participant_type": "market_actor",
        "reliability_rating": rating,
        "purchase_frequency": "weekly",
        "relationship_months": 24,
        "avg_volume_kg": 40,
    }


def group(cycles: int = 5) -> dict[str, Any]:
    return {
        "participant_type": "social_group",
        "consecutive_cycles": cycles,
        "last_contribution_date": (date.today() - timedelta(days=10)).isoformat(),
        "contribution_amount": 500,
    }


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def reject(client: httpx.Client, name: str, method: str, path: str, **kw: Any) -> httpx.Response:
    response = call(client, method, path, **kw)
    check(name, 400 <= response.status_code < 500, f"got {response.status_code}")
    return response


def no_crash(client: httpx.Client, name: str, method: str, path: str, **kw: Any) -> httpx.Response:
    response = call(client, method, path, **kw)
    check(name, response.status_code < 500, f"got {response.status_code}")
    return response


def start_session(client: httpx.Client, farmer_id: str) -> tuple[str, dict[str, str]]:
    sid = ok(client, "POST", "/api/verify/start", json={"farmer_id": farmer_id})["session_id"]
    participants = ok(client, "GET", f"/api/verify/{sid}/status")["participants"]
    return sid, {p["participant_type"]: p["id"] for p in participants}


def respond_path(sid: str, pid: str) -> str:
    return f"/api/verify/{sid}/respond/{pid}"


def race(base_url: str, calls: list[tuple[str, str, Any]]) -> list[int]:
    """Fire the given (method, path, json) requests at the same instant."""
    barrier = threading.Barrier(len(calls))

    def fire(spec: tuple[str, str, Any]) -> int:
        method, path, payload = spec
        with httpx.Client(base_url=base_url, timeout=120.0) as client:
            barrier.wait()
            return client.request(method, path, json=payload).status_code

    with ThreadPoolExecutor(max_workers=len(calls)) as pool:
        return sorted(pool.map(fire, calls))


# --------------------------------------------------------------------------
# batteries
# --------------------------------------------------------------------------
def battery_validation(client: httpx.Client, base_url: str) -> None:
    step("A. Bad input must be rejected with a 4xx, never crash")
    unknown = str(uuid.uuid4())

    missing = farmer_payload()
    del missing["full_name"]
    reject(client, "farmer missing a required field", "POST", "/api/farmers", json=missing)
    reject(client, "farmer with a wrongly typed field", "POST", "/api/farmers",
           json=farmer_payload(years_farming="many"))

    original = farmer_payload()
    ok(client, "POST", "/api/farmers", json=original)
    reject(client, "second farmer with the same national_id and phone",
           "POST", "/api/farmers", json=original)

    farmer_id = ok(client, "POST", "/api/farmers", json=farmer_payload())["id"]
    farm_url = f"/api/farmers/{farmer_id}/farm"
    reject(client, "farm with latitude out of range", "POST", farm_url,
           json=farm_payload(latitude=123.0))
    reject(client, "farm with negative acreage", "POST", farm_url,
           json=farm_payload(acreage=-2))
    reject(client, "farm for a farmer that does not exist", "POST",
           f"/api/farmers/{unknown}/farm", json=farm_payload())
    reject(client, "GET unknown farmer", "GET", f"/api/farmers/{unknown}")
    reject(client, "GET farmer with a malformed id", "GET", "/api/farmers/not-a-uuid")

    reject(client, "verification for an unknown farmer", "POST", "/api/verify/start",
           json={"farmer_id": unknown})
    reject(client, "verification with a malformed farmer id", "POST", "/api/verify/start",
           json={"farmer_id": "nope"})
    reject(client, "result for an unknown session", "GET", f"/api/verify/{unknown}/result")
    reject(client, "explanation for an unknown session", "GET",
           f"/api/verify/{unknown}/explanation")

    def loan(**overrides: Any) -> dict[str, Any]:
        body = {"farmer_id": farmer_id, "amount": 100.0, "purpose": "farming_inputs",
                "duration_months": 6, "interest_rate": 10.0}
        body.update(overrides)
        return body

    reject(client, "loan of zero", "POST", "/api/loans", json=loan(amount=0))
    reject(client, "negative loan", "POST", "/api/loans", json=loan(amount=-50))
    reject(client, "loan for a farmer with no score", "POST", "/api/loans", json=loan())
    reject(client, "loan for an unknown farmer", "POST", "/api/loans",
           json=loan(farmer_id=unknown))
    for action in ("disburse", "repay", "default"):
        reject(client, f"{action} an unknown loan", "POST", f"/api/loans/{unknown}/{action}")
        reject(client, f"{action} a loan with a malformed id", "POST", f"/api/loans/nope/{action}")


def battery_responses(client: httpx.Client, base_url: str) -> None:
    step("B. Illegal verification responses must be rejected")
    farmer_id = create_farmer_with_verifiers(client, "RESP")
    sid, parts = start_session(client, farmer_id)
    t, m, g = parts["trust_source"], parts["market_actor"], parts["social_group"]

    reject(client, "rating 0", "POST", respond_path(sid, t), json=trust(0))
    reject(client, "rating 5", "POST", respond_path(sid, t), json=trust(5))
    reject(client, "buyer payload sent to a trust-source participant",
           "POST", respond_path(sid, t), json=buyer())
    reject(client, "unknown participant id", "POST",
           respond_path(sid, str(uuid.uuid4())), json=trust())

    other_sid, other_parts = start_session(client, farmer_id)
    reject(client, "participant that belongs to a different session", "POST",
           respond_path(sid, other_parts["trust_source"]), json=trust())

    for pid, payload in ((t, trust()), (m, buyer()), (g, group())):
        ok(client, "POST", respond_path(sid, pid), json=payload)

    again = call(client, "POST", respond_path(sid, t), json=trust())
    check("answering twice is a 409", again.status_code == 409, f"got {again.status_code}")

    reject(client, "explanation with an invalid mode", "GET",
           f"/api/verify/{sid}/explanation", params={"mode": "banana"})


def battery_no_signal(client: httpx.Client, base_url: str) -> None:
    step("C. Nobody answers: an empty signal set must not crash the service")
    farmer_id = create_farmer_with_verifiers(client, "SILENT")
    sid, parts = start_session(client, farmer_id)
    for kind, pid in parts.items():
        no_crash(client, f"timing out the {kind} participant", "POST",
                 f"/api/verify/{sid}/timeout/{pid}")
    result = call(client, "GET", f"/api/verify/{sid}/result")
    check("no score exists when every verifier timed out (4xx, not 5xx)",
          400 <= result.status_code < 500, f"got {result.status_code}")


def battery_unknown_respondent(client: httpx.Client, base_url: str) -> None:
    step("D. A verifier who does not know the farmer contributes nothing")
    farmer_id = create_farmer_with_verifiers(client, "UNKNOWN")
    sid, parts = start_session(client, farmer_id)
    ok(client, "POST", respond_path(sid, parts["trust_source"]), json=trust(4, known=False))
    ok(client, "POST", respond_path(sid, parts["market_actor"]), json=buyer(4))
    ok(client, "POST", respond_path(sid, parts["social_group"]), json=group(5))

    score = ok(client, "GET", f"/api/verify/{sid}/result")["score_profile"]
    want = (BUYER_W * scaled(4) + DISCIPLINE_W * 75.0) / (BUYER_W + DISCIPLINE_W)
    got = float(score["character_score"])
    check("testimony is excluded and the remaining weights renormalise",
          abs(got - want) <= TOLERANCE, f"expected {want:.2f}, got {got:.2f}")


def battery_races(client: httpx.Client, base_url: str) -> None:
    step("E. Races: exactly one request may win")

    farmer_id = create_farmer_with_verifiers(client, "RACE1")
    sid, parts = start_session(client, farmer_id)
    spec = ("POST", respond_path(sid, parts["trust_source"]), trust())
    codes = race(base_url, [spec, spec])
    check("two simultaneous answers from one verifier: one wins, one is refused",
          codes == [200, 409], f"got {codes}")

    farmer_id = create_farmer_with_verifiers(client, "RACE2")
    sid, parts = start_session(client, farmer_id)
    ok(client, "POST", respond_path(sid, parts["trust_source"]), json=trust())
    codes = race(base_url, [
        ("POST", respond_path(sid, parts["market_actor"]), buyer()),
        ("POST", respond_path(sid, parts["social_group"]), group()),
    ])
    check("the last two answers arriving together both succeed",
          codes == [200, 200], f"got {codes}")
    result = call(client, "GET", f"/api/verify/{sid}/result")
    check("the session still completes and produces a score",
          result.status_code == 200, f"got {result.status_code}")

    farmer_id = create_farmer_with_verifiers(client, "RACE3")
    profile = verify_round(client, farmer_id, 4, 4, cycles=5)
    loan = take_loan(client, farmer_id, min(500.0, recommended(profile)))
    disburse = ("POST", f"/api/loans/{loan['id']}/disburse", None)
    codes = race(base_url, [disburse, disburse])
    check("two simultaneous disbursements: one wins, one is refused",
          codes == [200, 409], f"got {codes}")
    default = ("POST", f"/api/loans/{loan['id']}/default", None)
    codes = race(base_url, [default, default])
    check("two simultaneous defaults: one wins, one is refused",
          codes == [200, 409], f"got {codes}")


def battery_ceiling(client: httpx.Client, base_url: str) -> None:
    step("F. A clean repayment record must never push a score past 100")
    farmer_id = create_farmer_with_verifiers(client, "CEILING")
    for round_no in range(1, CEILING_ROUNDS + 1):
        profile = verify_round(client, farmer_id, 4, 4, cycles=7)
        character = float(profile["character_score"])
        final = float(profile["final_score"])
        check(f"round {round_no}: scores stay within 0-100",
              0.0 <= character <= 100.0 and 0.0 <= final <= 100.0,
              f"character={character} final={final}")
        loan = take_loan(client, farmer_id, min(100.0, recommended(profile)))
        ok(client, "POST", f"/api/loans/{loan['id']}/disburse")
        ok(client, "POST", f"/api/loans/{loan['id']}/repay")


def probe_policy(client: httpx.Client, base_url: str) -> None:
    step("G. Policy probe (informational, not pass/fail)")
    farmer_id = create_farmer_with_verifiers(client, "POLICY")
    profile = verify_round(client, farmer_id, 4, 4, cycles=5)
    limit = recommended(profile)
    first = take_loan(client, farmer_id, limit)
    second = call(client, "POST", "/api/loans", json={
        "farmer_id": farmer_id, "amount": limit, "purpose": "farming_inputs",
        "duration_months": 6, "interest_rate": 10.0,
    })
    print(f"INFO: loan 1 ({first['id']}) accepted; a second open loan of the same size "
          f"returned {second.status_code}. If that is 200, one farmer can hold several "
          f"open loans of {limit} each. Decide whether total outstanding exposure should "
          "be capped.")


# --------------------------------------------------------------------------
def run(base_url: str) -> int:
    batteries = (
        battery_validation,
        battery_responses,
        battery_no_signal,
        battery_unknown_respondent,
        battery_races,
        battery_ceiling,
        probe_policy,
    )
    for battery in batteries:
        # Fresh client per battery so one server crash cannot poison the next.
        with httpx.Client(base_url=base_url, timeout=120.0) as client:
            try:
                battery(client, base_url)
            except Exception as exc:
                check(f"{battery.__name__} ran to completion", False,
                      f"{type(exc).__name__}: {exc}")

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