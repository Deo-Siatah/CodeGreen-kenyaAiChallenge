import uuid
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class ScoreProfile(Base, TimestampMixin):
    """One immutable scoring run. Recomputation appends a new version rather
    than overwriting (design doc 3.4), so a loan officer can see how a score
    moved and a future model has the raw outcome history to calibrate against.

    NOTE: the partial unique index that enforces a single current profile per
    farmer ("UNIQUE (farmer_id) WHERE is_current = true") is intentionally NOT
    declared here. It is added in the Alembic migration via:
        op.create_index(
            "ix_score_profiles_current", "score_profiles",
            ["farmer_id"], unique=True, postgresql_where=sa.text("is_current = true"),
        )
    The index name is ix_score_profiles_current, following the default
    naming_convention. Because the model omits it, a future autogenerate will
    propose dropping it - that is expected, and the drop should be rejected.
    """

    __tablename__ = "score_profiles"
    __table_args__ = (
        CheckConstraint(
            "character_score BETWEEN 0 AND 100",
            name="character_score_between_0_and_100",
        ),
        CheckConstraint(
            "capacity_score BETWEEN 0 AND 100", name="capacity_score_between_0_and_100"
        ),
        CheckConstraint(
            "final_score BETWEEN 0 AND 100", name="final_score_between_0_and_100"
        ),
        Index(
            "ix_score_profiles_current", 
            "farmer_id", 
            unique=True, 
            postgresql_where="is_current = true"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farmers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    character_score: Mapped[float] = mapped_column(
        Numeric(5, 2, asdecimal=False), nullable=False
    )
    capacity_score: Mapped[float] = mapped_column(
        Numeric(5, 2, asdecimal=False), nullable=True
    )
    final_score: Mapped[float] = mapped_column(
        Numeric(5, 2, asdecimal=False), nullable=False
    )
    decision: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    recommended_amount: Mapped[float | None] = mapped_column(
        Numeric(12, 2, asdecimal=False), nullable=True
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ScoreComponent(Base, TimestampMixin):
    """One line of the explainability breakdown (design doc 3.2).

    Every score writes its full component list — that record is what makes a
    later fairness audit ("do women systematically score lower on component X?")
    possible at all.

    pool_id groups the several testimony rows that were averaged into one
    component (3 neighbors -> 1 pooled testimony component, 3.5), so the
    breakdown can still be expanded back to the individual respondents.
    """

    __tablename__ = "score_components"
    __table_args__ = (
        CheckConstraint(
            "axis IN ('character', 'capacity')", name="axis_character_or_capacity"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    score_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("score_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    axis: Mapped[str] = mapped_column(String(16), nullable=False)
    component_name: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_value: Mapped[str] = mapped_column(Text, nullable=False)
    contribution: Mapped[float | None] = mapped_column(
        Numeric(12, 2, asdecimal=False), nullable=True
    )
    weight: Mapped[float | None] = mapped_column(
        Numeric(6, 4, asdecimal=False), nullable=True
    )
    pool_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    market_actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("market_actors.id", ondelete="SET NULL"), 
        nullable=True, 
        index=True
    )
    trust_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("trust_sources.id", ondelete="SET NULL"), 
        nullable=True, 
        index=True
    )
