"""Credibility formula tests.

Pure arithmetic, no database and no session: _credibility_score is the single
place the placeholder formula lives, so it is cheap to pin down exactly.
"""

import pytest

from repositories.credibility_repository import (
    CREDIBILITY_CEILING,
    CREDIBILITY_FLOOR,
    CREDIBILITY_NEUTRAL,
    _credibility_score,
)


def test_new_verifier_is_neutral():
    """phase2.md 5.1: a new verifier starts neutral at 1.0."""
    assert _credibility_score(0, 0) == 1.0
    assert CREDIBILITY_NEUTRAL == 1.0


@pytest.mark.parametrize(
    "repaid,defaulted,expected",
    [
        (1, 0, 1.083),
        (10, 0, 1.333),
        (0, 10, 0.667),
    ],
)
def test_specified_values(repaid, defaulted, expected):
    """The worked values from the specification, to three decimals."""
    assert round(_credibility_score(repaid, defaulted), 3) == expected


def test_many_repaid_approaches_the_ceiling_without_reaching_it():
    """Approaches 1.5 as the record grows, and never exceeds it.

    The damping term is what does this: the ratio saturates, so 1 + 0.5 = 1.5
    is a limit that is approached rather than a ceiling that is hit. (1, 0) is
    only 1.083, so a single endorsement buys very little.
    """
    assert CREDIBILITY_NEUTRAL < _credibility_score(10, 0) < CREDIBILITY_CEILING
    assert _credibility_score(1000, 0) < CREDIBILITY_CEILING
    assert round(_credibility_score(1000, 0), 3) == 1.498


def test_many_defaulted_approaches_the_floor_without_reaching_it():
    assert CREDIBILITY_FLOOR < _credibility_score(0, 10) < CREDIBILITY_NEUTRAL
    assert _credibility_score(0, 1000) > CREDIBILITY_FLOOR
    assert round(_credibility_score(0, 1000), 3) == 0.502


@pytest.mark.parametrize(
    "repaid,defaulted",
    [
        (0, 0),
        (1, 0),
        (0, 1),
        (5, 0),
        (0, 5),
        (3, 3),
        (50, 1),
        (1, 50),
        (999, 999),
        (10_000, 0),
        (0, 10_000),
        (10_000, 10_000),
    ],
)
def test_score_always_within_bounds(repaid, defaulted):
    """The range is bounded by the formula, not by a clamp at the boundary.

    This is the invariant that replaced the explicit min/max, so it is asserted
    over a wide sweep rather than only at the cases named in the spec.
    """
    score = _credibility_score(repaid, defaulted)
    assert CREDIBILITY_FLOOR <= score <= CREDIBILITY_CEILING


def test_repaid_raises_and_default_lowers():
    """Monotonic in the right direction across a matched pair."""
    assert (
        _credibility_score(5, 2)
        > _credibility_score(3, 2)
        > _credibility_score(1, 2)
    )
    assert _credibility_score(0, 0) > _credibility_score(1, 2) > CREDIBILITY_FLOOR
    # Same total outcomes, better mix -> higher score.
    assert _credibility_score(3, 1) > _credibility_score(1, 3)


def test_asymptotes_are_never_reached():
    """The limits are open, so no input pins a verifier at the extreme."""
    assert _credibility_score(10_000_000, 0) < CREDIBILITY_CEILING
    assert _credibility_score(0, 10_000_000) > CREDIBILITY_FLOOR
