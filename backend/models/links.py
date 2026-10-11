import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class FarmerTrustSourceLink(Base, TimestampMixin):
    """Farmer <-VERIFIED_BY-> TrustSource, with relationship context."""

    __tablename__ = "farmer_trust_source_links"

    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farmers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    trust_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trust_sources.id", ondelete="CASCADE"),
        primary_key=True,
    )
    relationship_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    years_known: Mapped[int | None] = mapped_column(Integer, nullable=True)


class FarmerInstitutionLink(Base, TimestampMixin):
    __tablename__ = "farmer_institution_links"

    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farmers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    membership_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    joined_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class FarmerSocialGroupLink(Base, TimestampMixin):
    __tablename__ = "farmer_social_group_links"

    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farmers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    social_group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("social_groups.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    joined_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class FarmerMarketActorLink(Base, TimestampMixin):
    __tablename__ = "farmer_market_actor_links"

    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farmers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    market_actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("market_actors.id", ondelete="CASCADE"),
        primary_key=True,
    )
    relationship_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    since_date: Mapped[date | None] = mapped_column(Date, nullable=True)
