"""Loan service for managing loan lifecycle.

This service handles loan creation, disbursement, and resolution, following
the business logic established in Section 14 and Section 15.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.loan import Loan
from repositories.scoring_repository import ScoringRepository
from services.loan_resolution_service import LoanResolutionService
from services.audit_service import AuditService


class LoanError(Exception):
    """Base class for loan-related errors."""
    pass


class NoScoreError(LoanError):
    """Raised when a farmer has no score profile."""
    pass


class LoanNotEligibleError(LoanError):
    """Raised when a farmer is not eligible for a loan."""
    pass


class AmountExceedsRecommendationError(LoanError):
    """Raised when loan amount exceeds recommended amount."""
    pass


class OpenLoanExistsError(LoanError):
    """Raised when farmer already has an open loan."""
    pass


class LoanNotFoundError(ValueError):
    """Raised when a loan lookup returns nothing."""
    pass


class InvalidLoanStateError(ValueError):
    """Raised when a loan status precondition fails."""
    pass


class LoanService:
    """Handle loan creation, disbursement, and resolution."""

    def __init__(
        self,
        loan_resolution_service: LoanResolutionService | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.loan_resolution_service = loan_resolution_service or LoanResolutionService()
        self.audit_service = audit_service or AuditService()

    async def create_loan(
        self,
        session: AsyncSession,
        farmer_id: uuid.UUID | str,
        amount: float,
        purpose: str | None = None,
        duration_months: int | None = None,
        interest_rate: float | None = None,
    ) -> Loan:
        """Create a new loan for a farmer.
        
        Validates against farmer's current score recommendation.
        Sets status="pending_disbursement".
        """
        # Get farmer's current score
        scoring_repository = ScoringRepository()
        profile = await scoring_repository.get_current_score(session, farmer_id)
        
        if profile is None:
            raise NoScoreError(f"Farmer {farmer_id} has no score profile")
        
        if profile.recommended_amount is None:
            raise LoanNotEligibleError(f"Farmer {farmer_id} is not eligible for a loan")
        
        if amount > profile.recommended_amount:
            raise AmountExceedsRecommendationError(
                f"Loan amount {amount} exceeds recommended amount {profile.recommended_amount}"
            )
        
        # Check for existing open loans under row lock
        farmer_loans_result = await session.execute(
            select(Loan).where(
                Loan.farmer_id == farmer_id,
                Loan.status.in_(["pending_disbursement", "disbursed"])
            ).with_for_update()
        )
        existing_loans = farmer_loans_result.scalars().all()
        if existing_loans:
            raise OpenLoanExistsError(f"Farmer {farmer_id} already has an open loan")
        
        loan = Loan(
            farmer_id=farmer_id,
            amount=amount,
            purpose=purpose,
            duration_months=duration_months,
            interest_rate=interest_rate,
            status="pending_disbursement",
            applied_at=datetime.now(timezone.utc),
            score_profile_id=profile.id,
        )
        
        session.add(loan)
        await session.flush()
        
        # Log the loan creation
        await self.audit_service.write_log(
            session,
            actor_type="system",
            actor_id=None,
            action="loan_created",
            entity_type="loan",
            entity_id=loan.id,
            details={"amount": amount, "farmer_id": str(farmer_id)},
        )
        
        return loan

    async def mark_disbursed(
        self,
        session: AsyncSession,
        loan_id: uuid.UUID | str,
    ) -> Loan:
        """Mark a loan as disbursed.
        
        Sets status="disbursed" and disbursed_at timestamp.
        Requires loan to be in "pending_disbursement" status.
        """
        # Get the loan with row lock to prevent race conditions
        result = await session.execute(
            select(Loan).where(Loan.id == loan_id).with_for_update()
        )
        loan = result.scalar_one_or_none()
        if loan is None:
            raise LoanNotFoundError(f"Loan {loan_id} not found")
        
        if loan.status != "pending_disbursement":
            raise InvalidLoanStateError(f"Loan {loan_id} is not pending disbursement, current status: {loan.status}")
        
        loan.status = "disbursed"
        loan.disbursed_at = datetime.now(timezone.utc)
        
        await session.flush()
        
        # Log the disbursement
        await self.audit_service.write_log(
            session,
            actor_type="system",
            actor_id=None,
            action="loan_disbursed",
            entity_type="loan",
            entity_id=loan_id,
            details={"amount": loan.amount, "farmer_id": str(loan.farmer_id)},
        )
        
        return loan

    async def resolve_loan(
        self,
        session: AsyncSession,
        loan_id: uuid.UUID | str,
        outcome: Literal["repaid", "defaulted"],
        resolved_at: datetime | None = None,
    ) -> Loan:
        """Resolve a loan (repay or default).
        
        Requires loan to be in "disbursed" status.
        Updates loan status and calls loan resolution service to update credibility.
        """
        # Get the loan with row lock to prevent race conditions
        result = await session.execute(
            select(Loan).where(Loan.id == loan_id).with_for_update()
        )
        loan = result.scalar_one_or_none()
        if loan is None:
            raise LoanNotFoundError(f"Loan {loan_id} not found")
        
        if loan.status != "disbursed":
            raise InvalidLoanStateError(f"Loan {loan_id} is not disbursed, cannot resolve. Current status: {loan.status}")
        
        # Use provided timestamp or current time
        resolved_at = resolved_at or datetime.now(timezone.utc)
        
        # Update loan status
        if outcome == "repaid":
            loan.status = "repaid"
            loan.repaid_at = resolved_at
        else:
            loan.status = "defaulted"
            loan.defaulted_at = resolved_at
        
        # Call loan resolution service to update credibility
        await self.loan_resolution_service.update_credibility_for_loan(
            session, loan.score_profile_id, outcome
        )
        
        await session.flush()
        
        # Log the resolution
        await self.audit_service.write_log(
            session,
            actor_type="system",
            actor_id=None,
            action="loan_resolved",
            entity_type="loan",
            entity_id=loan_id,
            details={"outcome": outcome, "resolved_at": resolved_at.isoformat()},
        )
        
        return loan