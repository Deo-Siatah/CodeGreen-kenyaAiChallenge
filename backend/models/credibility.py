import uuid
from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class VerifierCredibility(Base, TimestampMixin):
    """An evolving track record per verifier, replacing static category weights.

    A chief who has endorsed five farmers, three of whom defaulted, carries
    less weight than one with a clean record regardless of title (design doc 5.1).
    credibility_score is the multiplier applied to that verifier's testimony.
    """

    __tablename__ = "verifier_credibility"
    __table_args__ = (
        CheckConstraint(
            "subject_type IN ('trust_source', 'market_actor')",
            name="subject_type_trust_source_or_market_actor"
        ),
        UniqueConstraint("subject_type", "subject_id", name="uq_verifier_credibility_subject"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    total_endorsements: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    repaid_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    defaulted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    credibility_score: Mapped[float] = mapped_column(
        Numeric(6, 3, asdecimal=False), default=1.0, nullable=False
    )


class FraudFlag(Base, TimestampMixin):
    """A structural review flag, never an automatic decline (design doc 5.5).

    subject_id is polymorphic — reciprocal endorsement loops, verifier fan-out
    and synchronised submission timing can each be flagged against a farmer, a
    verifier or a whole session. Validated at the service layer.
    """

    __tablename__ = "fraud_flags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    subject_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    flag_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), default="low", nullable=False)
    raised_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
