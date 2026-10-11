import uuid
from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class Institution(Base, TimestampMixin):
    __tablename__ = "institutions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(
        String(64), index=True, nullable=True
    )
    county: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)


class TrustSource(Base, TimestampMixin):
    """A community respondent: chief, elder, school head, religious leader, etc.

    The registered phone is what binds a USSD/SMS response back to this person
    (identity-level verification, design doc 2.3).
    """

    __tablename__ = "trust_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    national_id: Mapped[str | None] = mapped_column(
        String(64), index=True, nullable=True
    )
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )


class SocialGroup(Base, TimestampMixin):
    __tablename__ = "social_groups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    group_type: Mapped[str | None] = mapped_column(
        String(64), index=True, nullable=True
    )
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    formation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)


class MarketActor(Base, TimestampMixin):
    """Buyer, aggregator or agrovet — the transactional side of the network."""

    __tablename__ = "market_actors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_type: Mapped[str | None] = mapped_column(
        String(64), index=True, nullable=True
    )
    phone: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
