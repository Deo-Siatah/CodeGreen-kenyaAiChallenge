import uuid
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from models.credibility import VerifierCredibility
from repositories.credibility_repository import CredibilityRepository
from services.audit_service import AuditService


class CredibilityService:
    def __init__(
        self,
        repository: CredibilityRepository | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.repository = repository or CredibilityRepository()
        self.audit_service = audit_service or AuditService()

    async def get_or_create(
        self, session: AsyncSession, subject_type: str, subject_id: uuid.UUID | str
    ) -> VerifierCredibility:
        """Get or create a verifier credibility record for a subject."""
        return await self.repository.get_or_create_credibility(
            session, subject_type, subject_id
        )

    async def record_loan_outcome(
        self,
        session: AsyncSession,
        subject_type: str,
        subject_id: uuid.UUID | str,
        outcome: Literal["repaid", "defaulted"],
    ) -> VerifierCredibility:
        """Record a loan outcome and update credibility, then log the change.

        Does not commit - called from inside a loan-resolution transaction.
        """
        credibility = await self.repository.update_credibility_on_loan_outcome(
            session, subject_type, subject_id, repaid=outcome == "repaid"
        )
        await self.audit_service.write_log(
            session,
            actor_type="system",
            actor_id=None,
            action="credibility_updated",
            entity_type="verifier_credibility",
            entity_id=subject_id,
            details={"outcome": outcome, "subject_type": subject_type},
        )
        return credibility