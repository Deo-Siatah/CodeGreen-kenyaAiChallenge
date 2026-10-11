import uuid
from datetime import date
from uuid import uuid4

from sqlalchemy import Date, Float, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class Farmer(Base, TimestampMixin):
    __tablename__ = "farmers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # unique=True + index=True emits a single UNIQUE index (lookup + dedup).
    national_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    phone: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    gender: Mapped[str] = mapped_column(String(32), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    village: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sub_county: Mapped[str | None] = mapped_column(String(128), nullable=True)
    county: Mapped[str | None] = mapped_column(String(128), nullable=True)
    farming_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Context only, never a scoring input (design doc 3.3).
    years_farming: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Farm(Base, TimestampMixin):
    __tablename__ = "farms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farmers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    acreage: Mapped[float | None] = mapped_column(
        Numeric(10, 2, asdecimal=False), nullable=True
    )
    production_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    irrigation_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Required for the Sentinel-2 / Earth Engine pull keyed on farm coordinates.
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
