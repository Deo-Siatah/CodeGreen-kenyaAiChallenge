"""Loan resolution service: update verifier credibility when loans are resolved.

This service handles the business logic of updating verifier credibility when
loans are resolved (repaid or defaulted), following the pattern established
in Section 14 for trust sources and extended in Section 15 for market actors.
"""

from __future__ import annotations

import uuid
from typing import Literal
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.loan import Loan
from models.scoring import ScoreComponent
from services.credibility_service import CredibilityService
from services.audit_service import AuditService


class LoanResolutionService:
    """Handle loan resolution and update associated credibilities."""

    def __init__(
        self,
        credibility_service: CredibilityService | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.credibility_service = credibility_service or CredibilityService()
        self.audit_service = audit_service or AuditService()

    async def update_credibility_for_loan(
        self,
        session: AsyncSession,
        score_profile_id: uuid.UUID | None,
        outcome: Literal["repaid", "defaulted"],
    ) -> None:
        """Update credibility for trust sources and market actors based on loan outcome.
        
        This method ONLY handles credibility updates and does NOT touch loan status.
        """
        # Update trust_source credibility (Section 14 pattern)
        if score_profile_id:
            await self._update_trust_source_credibility(session, score_profile_id, outcome)
        
        # Update market_actor credibility (Section 15 pattern)
        if score_profile_id:
            await self._update_market_actor_credibility(session, score_profile_id, outcome)

    async def _update_trust_source_credibility(
        self,
        session: AsyncSession,
        score_profile_id: uuid.UUID,
        outcome: Literal["repaid", "defaulted"],
    ) -> None:
        """Update trust_source credibility based on testimony components."""
        # Query score_components for trust_source testimony
        result = await session.execute(
            select(ScoreComponent.trust_source_id)
            .where(
                ScoreComponent.score_profile_id == score_profile_id,
                ScoreComponent.axis == "character",
                ScoreComponent.component_name == "testimony",
                ScoreComponent.trust_source_id.isnot(None),
            )
            .distinct()
        )
        trust_source_ids = {row[0] for row in result.all()}
        
        # Update credibility for each distinct trust_source found
        for trust_source_id in trust_source_ids:
            await self.credibility_service.record_loan_outcome(
                session, "trust_source", trust_source_id, outcome
            )

    async def _update_market_actor_credibility(
        self,
        session: AsyncSession,
        score_profile_id: uuid.UUID,
        outcome: Literal["repaid", "defaulted"],
    ) -> None:
        """Update market_actor credibility based on buyer_relationship components."""
        # Query score_components for buyer_relationship (excluding pool summary)
        result = await session.execute(
            select(ScoreComponent.market_actor_id)
            .where(
                ScoreComponent.score_profile_id == score_profile_id,
                ScoreComponent.axis == "character",
                ScoreComponent.component_name == "buyer_relationship",
                ScoreComponent.market_actor_id.isnot(None),  # Exclude pool summary
            )
            .distinct()
        )
        market_actor_ids = {row[0] for row in result.all()}
        
        # Update credibility for each distinct market_actor found
        for market_actor_id in market_actor_ids:
            await self.credibility_service.record_loan_outcome(
                session, "market_actor", market_actor_id, outcome
            )