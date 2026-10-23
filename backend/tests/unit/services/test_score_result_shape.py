"""`respond`/`timeout` declare `response_model=dict`.

Returning the `ScoreComputationResult` dataclass there left FastAPI to encode an
object that wraps an ORM row, which can fail response validation *after* the
participant's answer was committed. The helper exists so that payload is flat
and JSON-safe; these tests pin that contract without touching a database.
"""

import json
from types import SimpleNamespace
from uuid import uuid4

from services.verification_service import _score_result_dict


def test_flattens_the_score_computation_into_json_safe_values():
    profile_id = uuid4()
    result = SimpleNamespace(
        profile=SimpleNamespace(
            id=profile_id,
            character_score=71.25,
            capacity_score=None,
            final_score=68.0,
            decision="REVIEW_REQUIRED",
            recommended_amount=15000.0,
        ),
        axis_note="capacity axis unavailable - character only",
    )

    payload = _score_result_dict(result)

    assert payload == {
        "id": str(profile_id),
        "character_score": 71.25,
        "capacity_score": None,
        "final_score": 68.0,
        "decision": "REVIEW_REQUIRED",
        "recommended_amount": 15000.0,
        "axis_note": "capacity axis unavailable - character only",
    }
    json.dumps(payload)


def test_passes_through_a_plain_dict_and_leaves_none_none():
    assert _score_result_dict({"final_score": 50}) == {"final_score": 50}
    assert _score_result_dict(None) is None
