"""Loan repository for database operations."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.loan import Loan


class LoanRepository:
    """Stateless: the session is supplied per call."""

    async def get_loan(
        self, session: AsyncSession, loan_id: uuid.UUID | str
    ) -> Loan | None:
        """Fetch one loan, or None if there is no such row."""
        return await session.get(Loan, loan_id)

    async def get_loans(
        self, 
        session: AsyncSession, 
        farmer_id: uuid.UUID | str | None = None,
        status: str | None = None,
    ) -> list[Loan]:
        """Fetch loans, optionally filtered by farmer_id and/or status."""
        query = select(Loan)
        
        if farmer_id is not None:
            query = query.where(Loan.farmer_id == farmer_id)
        
        if status is not None:
            query = query.where(Loan.status == status)
        
        result = await session.execute(query)
        return list(result.scalars().all())

    async def create_loan(
        self, 
        session: AsyncSession, 
        loan_data: dict[str, Any]
    ) -> Loan:
        """Create a new loan."""
        loan = Loan(**loan_data)
        session.add(loan)
        await session.flush()
        return loan

    async def update_loan(
        self, 
        session: AsyncSession, 
        loan_id: uuid.UUID, 
        updates: dict[str, Any]
    ) -> Loan | None:
        """Update a loan and return the updated loan."""
        result = await session.execute(select(Loan).where(Loan.id == loan_id))
        loan = result.scalar_one_or_none()
        if loan is None:
            return None
        
        for key, value in updates.items():
            setattr(loan, key, value)
        
        await session.flush()
        return loan

    async def get_farmer_loans(
        self, 
        session: AsyncSession, 
        farmer_id: uuid.UUID | str
    ) -> list[Loan]:
        """Get all loans for a specific farmer."""
        query = select(Loan).where(Loan.farmer_id == farmer_id)
        result = await session.execute(query)
        return list(result.scalars().all())