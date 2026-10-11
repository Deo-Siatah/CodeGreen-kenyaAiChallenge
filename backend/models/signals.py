import uuid
from datetime import date
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class Testimonial(Base, TimestampMixin):
    """Community testimony: a 4-point forced-choice rating, no neutral midpoint.

    personal_knowledge_flag = False means the respondent did not know the farmer
    well enough to judge; that row is excluded from scoring entirely rather than
    counted as an average (design doc 3.5).
    """

    __tablename__ = "testimonials"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 4", name="rating_between_1_and_4"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("verification_participants.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    personal_knowledge_flag: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )


class BuyerTestimonial(Base, TimestampMixin):
    """Buyer-side relationship facts, keyed to the buyer participant in a session."""

    __tablename__ = "buyer_testimonials"
    __table_args__ = (
        CheckConstraint(
            "reliability_rating BETWEEN 1 AND 4",
            name="reliability_rating_between_1_and_4",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("verification_participants.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    purchase_frequency: Mapped[str | None] = mapped_column(String(64), nullable=True)
    relationship_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_volume_kg: Mapped[float | None] = mapped_column(
        Numeric(12, 2, asdecimal=False), nullable=True
    )
    reliability_rating: Mapped[int] = mapped_column(Integer, nullable=False)


class DisciplineProxy(Base, TimestampMixin):
    """Chama/SACCO contribution history — dated, numeric, not a character rating.

    This is the highest-weighted component of the character axis precisely
    because it is specific and checkable (design doc 3.1, 5.3).
    """

    __tablename__ = "discipline_proxies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("verification_participants.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    social_group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("social_groups.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    consecutive_cycles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_contribution_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    contribution_amount: Mapped[float | None] = mapped_column(
        Numeric(12, 2, asdecimal=False), nullable=True
    )


class InKindSettlementProof(Base, TimestampMixin):
    __tablename__ = "in_kind_settlement_proofs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farmers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # Counterparty may be a market actor, a trust source or a plain self-report,
    # so this is an untyped reference validated at the service layer.
    counterparty_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    settlement_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    estimated_value: Mapped[float | None] = mapped_column(
        Numeric(12, 2, asdecimal=False), nullable=True
    )
    verification_status: Mapped[str] = mapped_column(
        String(32), default="pending", index=True, nullable=False
    )


class FarmActivitySignal(Base, TimestampMixin):
    """Third-party observation of the plot (Sentinel-2 NDVI via Earth Engine).

    The only signal with no human respondent, and structurally the hardest to
    fabricate (design doc 2.3.3). Capacity axis.
    """

    __tablename__ = "farm_activity_signals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farms.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    ndvi_value: Mapped[float | None] = mapped_column(
        Numeric(6, 4, asdecimal=False), nullable=True
    )
    cultivation_continuity_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2, asdecimal=False), nullable=True
    )
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="sentinel2", nullable=False)
