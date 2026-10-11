import uuid
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class VerificationSession(Base, TimestampMixin):
    __tablename__ = "verification_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farmers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32), default="pending", index=True, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Demo mode shortens timeout windows only; the scoring/session code path is
    # the same one production takes (design doc 4, step 4).
    demo_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class VerificationParticipant(Base, TimestampMixin):
    """One respondent contacted in a session.

    participant_id points at trust_sources / market_actors / social_groups
    depending on participant_type. It carries no FK: one polymorphic column
    cannot reference three tables, and a CHECK constraint plus a foreign key
    can't express "the referenced table must match participant_type" either.
    The service layer validates the id against participant_type on write.
    """

    __tablename__ = "verification_participants"
    __table_args__ = (
        CheckConstraint(
            "participant_type IN ('trust_source', 'market_actor', 'social_group')",
            name="participant_type_valid",
        ),
        UniqueConstraint(
            "session_id",
            "participant_type",
            "participant_id",
            # Explicit name: the naming convention would generate a 71-character
            # identifier, over Postgres' 63-character limit.
            name="uq_session_participant_identity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("verification_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    participant_type: Mapped[str] = mapped_column(String(32), nullable=False)
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
