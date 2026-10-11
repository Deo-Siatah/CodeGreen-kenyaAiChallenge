import uuid
from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class Loan(Base, TimestampMixin):
    """A loan resolved here (repaid or defaulted) is the outcome data that
    feeds verifier credibility and eventual weight recalibration
    (design doc 3.4, 5.1).
    """

    __tablename__ = "loans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farmers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # Nullable: an officer can originate a loan by hand, without a score run.
    score_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("score_profiles.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    amount: Mapped[float] = mapped_column(
        Numeric(12, 2, asdecimal=False), nullable=False
    )
    purpose: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interest_rate: Mapped[float | None] = mapped_column(
        Numeric(5, 2, asdecimal=False), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32), default="pending", index=True, nullable=False
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    disbursed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    repaid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    defaulted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
