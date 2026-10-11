"""Rating validation and the empty-signals contract.

Pure unit tests, no database: the 1-4 check runs in Python before the ORM ever
sees a value, and the empty-FarmerSignals shape is a constructor question. The
tests that need Postgres are in test_signal_repositories.py.
"""

import pytest

from models.signals import FarmActivitySignal
from repositories.exceptions import DomainError, RatingOutOfRange
from repositories.signal_repository import (
    MAX_RATING,
    MIN_RATING,
    FarmerSignals,
    _check_rating,
)


def test_scale_bounds_are_one_to_four():
    assert (MIN_RATING, MAX_RATING) == (1, 4)


@pytest.mark.parametrize("value", [1, 2, 3, 4])
def test_in_range_passes_through_unchanged(value):
    assert _check_rating(value, field="rating") == value


@pytest.mark.parametrize("value", [0, 5, -1, 100])
def test_out_of_range_rejected(value):
    with pytest.raises(RatingOutOfRange):
        _check_rating(value, field="rating")


@pytest.mark.parametrize("value", [2.5, 1.5, 4.0])
def test_fractional_rejected(value):
    """2.5 would pass a bare range check, then fail at the database.

    Numeric(5, 2) would silently accept 2.5 and round, or the integer column
    would reject it with a type error naming a Postgres type. Either way the
    caller gets a confusing failure from the wrong layer.
    """
    with pytest.raises(RatingOutOfRange):
        _check_rating(value, field="rating")


@pytest.mark.parametrize("value", ["3", None, [1], {"a": 1}])
def test_non_integer_rejected(value):
    with pytest.raises(RatingOutOfRange):
        _check_rating(value, field="rating")


@pytest.mark.parametrize("value", [True, False])
def test_bool_rejected_despite_being_an_int(value):
    """bool subclasses int, so True would otherwise pass as rating=1.

    A silent True -> 1 is exactly the kind of bug that reaches production as a
    mysteriously uniform rating column.
    """
    with pytest.raises(RatingOutOfRange):
        _check_rating(value, field="rating")


def test_reliability_rating_uses_the_same_check():
    """Both 1-4 columns share the validator, so neither can drift."""
    with pytest.raises(RatingOutOfRange):
        _check_rating(7, field="reliability_rating")


def test_error_message_names_the_field():
    with pytest.raises(RatingOutOfRange) as excinfo:
        _check_rating(9, field="reliability_rating")
    assert "reliability_rating" in str(excinfo.value)
    assert excinfo.value.field == "reliability_rating"
    assert excinfo.value.value == 9


def test_domain_error_is_a_value_error():
    """A ValueError subclass so existing `except ValueError` handlers catch it."""
    assert issubclass(RatingOutOfRange, DomainError)
    assert issubclass(DomainError, ValueError)


def test_empty_signals_is_valid_and_reports_empty():
    """A farmer with no signals yet is a normal result, not an error.

    This is the case the scoring service has to survive first, so it is pinned
    here: every field is an empty sequence, is_empty is True, and nothing is
    None.
    """
    empty = FarmerSignals(
        testimonials=[],
        buyer_testimonials=[],
        discipline_proxies=[],
        settlements=[],
        farm_activity=[],
    )
    assert empty.is_empty is True
    for field in FarmerSignals._fields:
        assert getattr(empty, field) == []
        assert getattr(empty, field) is not None


def test_partially_populated_signals_is_not_empty():
    """A farmer with one signal type is not 'empty'."""
    partial = FarmerSignals(
        testimonials=[],
        buyer_testimonials=[],
        discipline_proxies=[],
        settlements=[],
        farm_activity=[FarmActivitySignal()],
    )
    assert partial.is_empty is False
    assert partial.farm_activity != []


def test_signals_is_a_plain_tuple():
    """Unpackable, so the scoring service can read it positionally if it wants."""
    empty = FarmerSignals([], [], [], [], [])
    testimonials, buyer, discipline, settlements, activity = empty
    assert testimonials == [] and activity == []
