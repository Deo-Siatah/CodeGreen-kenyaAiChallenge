"""Domain errors raised before the database is involved.

These exist so a caller can tell "you asked for something that cannot exist"
apart from "the database rejected a row". Without them the only signal is an
IntegrityError carrying a raw CHECK-constraint name from Postgres, which leaks
schema detail to the API layer and reads to the caller as a server fault rather
than a validation mistake.
"""


class DomainError(ValueError):
    """Base class for input that is well-formed but semantically invalid."""


class RatingOutOfRange(DomainError):
    """A 1-4 forced-choice rating fell outside 1-4.

    One exception covers both the testimonial rating and the buyer reliability
    rating, since they share a scale: a caller catching this does not need to
    know which column it was.

    The scale is forced-choice with no neutral midpoint (design doc 3.5), which
    is why the valid range is the closed interval 1-4 and not 1-5.
    """

    def __init__(self, value: object, *, field: str = "rating") -> None:
        self.value = value
        self.field = field
        super().__init__(
            f"{field} must be an integer between 1 and 4 (inclusive); got "
            f"{value!r}. The scale is forced-choice with no neutral midpoint, so "
            "neither 0 nor 5 is valid."
        )
