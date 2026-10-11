from .audit import AuditLog
from .base import NAMING_CONVENTION, Base, TimestampMixin
from .credibility import FraudFlag, VerifierCredibility
from .farmer import Farm, Farmer
from .links import (
    FarmerInstitutionLink,
    FarmerMarketActorLink,
    FarmerSocialGroupLink,
    FarmerTrustSourceLink,
)
from .loan import Loan
from .scoring import ScoreComponent, ScoreProfile
from .signals import (
    BuyerTestimonial,
    DisciplineProxy,
    FarmActivitySignal,
    InKindSettlementProof,
    Testimonial,
)
from .trust import Institution, MarketActor, SocialGroup, TrustSource
from .verification import VerificationParticipant, VerificationSession

# Every model is imported and re-exported here so Alembic's autogenerate sees the
# full schema from a single import in env.py:
#     from backend.models import *   # noqa: F403
#     target_metadata = Base.metadata
__all__ = [
    "NAMING_CONVENTION",
    "AuditLog",
    "Base",
    "BuyerTestimonial",
    "DisciplineProxy",
    "Farm",
    "FarmActivitySignal",
    "Farmer",
    "FarmerInstitutionLink",
    "FarmerMarketActorLink",
    "FarmerSocialGroupLink",
    "FarmerTrustSourceLink",
    "FraudFlag",
    "InKindSettlementProof",
    "Institution",
    "Loan",
    "MarketActor",
    "ScoreComponent",
    "ScoreProfile",
    "SocialGroup",
    "Testimonial",
    "TimestampMixin",
    "TrustSource",
    "VerificationParticipant",
    "VerificationSession",
    "VerifierCredibility",
]
