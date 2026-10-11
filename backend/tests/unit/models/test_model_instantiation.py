r"""
Unit tests: every model re-exported from `backend/models/__init__.py` can be
constructed from its required fields alone, with no database, no engine and no
`.env` file.

`backend/models/` imports only `sqlalchemy`, `uuid`, `datetime` and its own
sibling modules -- it never touches `core.config` or `core.database`. So this
whole file runs offline, which is the point: it catches a column that was added
or made NOT NULL without a matching test value, before anyone reaches a real
database.

HOW TO RUN
----------
All commands are run from the `backend/` directory (the one holding
pyproject.toml, not the repo root):

    cd backend

With uv (creates/uses the project venv from pyproject.toml + uv.lock):

    uv run pytest tests/unit/models/test_model_instantiation.py -v
    uv run pytest tests/unit/models -v
    uv run pytest -v                        # whole suite, everything under tests/

Without uv (`.venv` already has pytest installed):

    .venv\Scripts\python -m pytest tests/unit/models/test_model_instantiation.py -v

One single test by id:

    uv run pytest "tests/unit/models/test_model_instantiation.py::test_required_only_matches_not_null_columns[Farmer]"

Useful flags:

    -x                      stop at the first failure
    -k rating               only tests whose id contains "rating"
    -q                      quiet
    -p no:cacheprovider     skip writing .pytest_cache

Running from the repo ROOT does not work -- `pythonpath = ["."]` in
pyproject.toml is resolved against the rootdir, so pytest must be invoked with
`backend` as the rootdir (i.e. cwd = backend/).

WHY THERE IS NO "rating must reject 5" TEST HERE
------------------------------------------------
`Testimonial.rating` and `BuyerTestimonial.reliability_rating` are enforced
solely by Postgres CHECK constraints (`ck_testimonials_rating_between_1_and_4`,
`ck_buyer_testimonials_reliability_rating_between_1_and_4`). There is no
Pydantic model and no Python validator on these SQLAlchemy classes, so
construction cannot and does not reject an out-of-range value --
`test_constructor_does_not_validate` below pins that behaviour on purpose.

The real rejection test therefore belongs in Section 3, against a real migrated
database: insert rating=0 and rating=5, assert both raise IntegrityError, then
assert rating=1..4 commit. That test needs a live Postgres, so it does not
belong in this file.
"""

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import CheckConstraint
from sqlalchemy.orm import DeclarativeBase

import models
from models import Base

# ---------------------------------------------------------------------------
# Required-field sample values, one entry per model.
#
# A field is "required" here when its column is NOT NULL and has neither a
# Python-side `default=` nor a `server_default=`, i.e. the value must come from
# the caller. Primary keys with `default=uuid4` and timestamps with
# `server_default=func.now()` are therefore NOT required.
# ---------------------------------------------------------------------------
_DT = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)

REQUIRED_FIELDS: dict[type, dict[str, object]] = {
    models.AuditLog: {
        "actor_type": "officer",
        "action": "score.approve",
        "entity_type": "loan",
        "entity_id": uuid.UUID(int=1),
    },
    models.BuyerTestimonial: {
        "participant_id": uuid.UUID(int=2),
        "reliability_rating": 3,
    },
    models.DisciplineProxy: {
        "participant_id": uuid.UUID(int=3),
        "social_group_id": uuid.UUID(int=4),
    },
    models.Farm: {"farmer_id": uuid.UUID(int=5)},
    models.FarmActivitySignal: {
        "farm_id": uuid.UUID(int=6),
        "observation_date": date(2026, 9, 1),
    },
    models.Farmer: {
        "full_name": "Amina Wanjiru",
        "national_id": "11902345",
        "phone": "+254700000001",
        "gender": "female",
        "location": "Nyeri",
    },
    models.FarmerInstitutionLink: {
        "farmer_id": uuid.UUID(int=7),
        "institution_id": uuid.UUID(int=8),
    },
    models.FarmerMarketActorLink: {
        "farmer_id": uuid.UUID(int=9),
        "market_actor_id": uuid.UUID(int=10),
    },
    models.FarmerSocialGroupLink: {
        "farmer_id": uuid.UUID(int=11),
        "social_group_id": uuid.UUID(int=12),
    },
    models.FarmerTrustSourceLink: {
        "farmer_id": uuid.UUID(int=13),
        "trust_source_id": uuid.UUID(int=14),
    },
    models.FraudFlag: {
        "subject_type": "farmer",
        "subject_id": uuid.UUID(int=15),
        "flag_type": "endorsement_loop",
    },
    models.InKindSettlementProof: {"farmer_id": uuid.UUID(int=16)},
    models.Institution: {"name": "Baraka Farmers Sacco"},
    models.Loan: {
        "farmer_id": uuid.UUID(int=17),
        "amount": 25000.0,
        "applied_at": _DT,
    },
    models.MarketActor: {"name": "FreshLink Aggregators"},
    models.ScoreComponent: {
        "score_profile_id": uuid.UUID(int=18),
        "axis": "character",
        "component_name": "pooled_testimony",
        "raw_value": "3 neighbours, mean 3.33",
    },
    models.ScoreProfile: {
        "farmer_id": uuid.UUID(int=19),
        "character_score": 72.5,
        "capacity_score": 61.0,
        "final_score": 68.25,
    },
    models.SocialGroup: {"name": "Kigumo Chama"},
    models.Testimonial: {
        "participant_id": uuid.UUID(int=20),
        "rating": 3,
    },
    models.TrustSource: {
        "full_name": "Chief Mwangi",
        "category": "village_leader",
    },
    models.VerificationParticipant: {
        "session_id": uuid.UUID(int=21),
        "participant_type": "trust_source",
        "participant_id": uuid.UUID(int=22),
    },
    models.VerificationSession: {"farmer_id": uuid.UUID(int=23)},
    models.VerifierCredibility: {"trust_source_id": uuid.UUID(int=24)},
}

MODEL_CASES = list(REQUIRED_FIELDS.items())


def _model_classes_exported() -> list[type]:
    """Every name in models.__all__ that is a mapped class (skips Base,
    TimestampMixin and the NAMING_CONVENTION dict)."""
    exported = []
    for name in models.__all__:
        obj = getattr(models, name)
        if (
            isinstance(obj, type)
            and issubclass(obj, DeclarativeBase)
            and obj is not Base
        ):
            exported.append(obj)
    return exported


def _columns_needing_caller_input(model: type) -> set[str]:
    """NOT NULL columns with no Python default and no server default."""
    return {
        col.name
        for col in model.__table__.columns
        if not col.nullable and col.default is None and col.server_default is None
    }


# ---------------------------------------------------------------------------
# Coverage: the registry above must track the package, in both directions.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("model", _model_classes_exported(), ids=lambda m: m.__name__)
def test_exported_model_has_required_field_fixtures(model):
    """Fails when a new model is re-exported from models/__init__.py without a
    required-field entry here, so the new model is not silently untested."""
    assert model in REQUIRED_FIELDS, (
        f"{model.__name__} is exported from backend.models but has no entry in "
        f"REQUIRED_FIELDS. Add one so its required fields are covered."
    )


@pytest.mark.parametrize(
    "model, _values", MODEL_CASES, ids=lambda v: getattr(v, "__name__", "")
)
def test_required_only_matches_not_null_columns(model, _values):
    """The fixture set is exactly the set of columns the caller must supply.
    Catches a column becoming required without a fixture, and a fixture for a
    column that is actually nullable or already defaulted."""
    expected = _columns_needing_caller_input(model)
    assert set(REQUIRED_FIELDS[model]) == expected


# ---------------------------------------------------------------------------
# The actual construction tests.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "model, kwargs", MODEL_CASES, ids=lambda v: getattr(v, "__name__", "")
)
def test_can_instantiate_with_required_fields_only(model, kwargs):
    """Constructs the model with nothing but its required fields. No engine, no
    session, no connection: this is pure Python object construction."""
    instance = model(**kwargs)

    assert isinstance(instance, model)
    for name, value in kwargs.items():
        assert getattr(instance, name) == value


@pytest.mark.parametrize(
    "model, kwargs", MODEL_CASES, ids=lambda v: getattr(v, "__name__", "")
)
def test_constructor_rejects_unknown_field(model, kwargs):
    """A typo like `relibility_rating` must fail loudly at construction rather
    than being silently dropped and then blowing up as a NOT NULL violation at
    flush time."""
    with pytest.raises(TypeError):
        model(**kwargs, definitely_not_a_real_field=1)


@pytest.mark.parametrize(
    "model, kwargs", MODEL_CASES, ids=lambda v: getattr(v, "__name__", "")
)
def test_optional_fields_left_unset_after_required_only_construction(model, kwargs):
    """Documents that Python-side defaults are applied by the INSERT statement,
    not by __init__ -- so a freshly constructed object legitimately reads None
    for defaulted columns."""
    instance = model(**kwargs)

    for col in model.__table__.columns:
        if (
            col.name in kwargs
            or col.default is not None
            or col.server_default is not None
        ):
            continue
        if col.nullable:
            assert getattr(instance, col.name) is None


@pytest.mark.parametrize(
    "model, kwargs", MODEL_CASES, ids=lambda v: getattr(v, "__name__", "")
)
def test_primary_key_default_applied_at_flush_not_at_construction(model, kwargs):
    """`default=uuid4` is a client-side default SQLAlchemy emits in the INSERT,
    so `id` is still None immediately after construction. If this ever starts
    failing, something changed about how defaults are wired."""
    pk_cols = [c for c in model.__table__.primary_key.columns]

    if len(pk_cols) != 1 or pk_cols[0].default is None:
        # Composite-PK link tables, or a PK without a default -- nothing to check.
        return

    instance = model(**kwargs)
    assert getattr(instance, pk_cols[0].name) is None


# ---------------------------------------------------------------------------
# Rating range: DB-only enforcement. See the module docstring.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("model", "column_name", "constraint_name"),
    [
        (models.Testimonial, "rating", "rating_between_1_and_4"),
        (
            models.BuyerTestimonial,
            "reliability_rating",
            "reliability_rating_between_1_and_4",
        ),
    ],
    ids=["testimonial_rating", "buyer_testimonial_reliability_rating"],
)
def test_rating_range_constraint_is_declared_in_metadata(
    model, column_name, constraint_name
):
    """The 1-4 rule exists as a named CHECK constraint in the table metadata.

    This is a metadata assertion ONLY -- it proves the constraint is declared
    and therefore that the Section 3 database test has something to fire on.
    It does not and cannot prove the value is rejected: enforcement happens in
    Postgres on INSERT. See the module docstring.
    """
    checks = [c for c in model.__table__.constraints if isinstance(c, CheckConstraint)]
    by_name = {c.name: c for c in checks}

    # Named explicitly in the model, then prefixed by NAMING_CONVENTION["ck"].
    assert (
        constraint_name in by_name
        or f"ck_{model.__table__.name}_{constraint_name}" in by_name
    )

    constraint = by_name.get(constraint_name) or by_name.get(
        f"ck_{model.__table__.name}_{constraint_name}"
    )
    sql = str(constraint.sqltext)
    assert column_name in sql
    assert "BETWEEN 1 AND 4" in sql


@pytest.mark.parametrize(
    ("model", "field", "kwargs"),
    [
        (models.Testimonial, "rating", {"participant_id": uuid.UUID(int=25)}),
        (
            models.BuyerTestimonial,
            "reliability_rating",
            {"participant_id": uuid.UUID(int=26)},
        ),
    ],
    ids=["testimonial_rating", "buyer_testimonial_reliability_rating"],
)
def test_constructor_does_not_validate_rating_range(model, field, kwargs):
    """Pins the current behaviour, and the reason the rejection test lives in
    Section 3: out-of-range ratings are accepted by the constructor. Nothing
    rejects them until Postgres applies the CHECK constraint on INSERT."""
    instance = model(**kwargs, **{field: 5})
    assert getattr(instance, field) == 5
