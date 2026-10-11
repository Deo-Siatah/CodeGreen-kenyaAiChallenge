"""Loan schemas for API validation."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class LoanCreate(BaseModel):
    """Request body for creating a new loan."""
    farmer_id: UUID = Field(..., description="ID of the farmer receiving the loan")
    amount: float = Field(..., gt=0, description="Loan amount")
    purpose: str | None = Field(None, description="Purpose of the loan")
    duration_months: int | None = Field(None, gt=0, description="Duration in months")
    interest_rate: float | None = Field(None, ge=0, description="Interest rate as percentage")


class LoanResponse(BaseModel):
    """Response schema for loan operations."""
    id: UUID
    farmer_id: UUID
    amount: float
    purpose: str | None
    duration_months: int | None
    interest_rate: float | None
    status: str
    applied_at: datetime
    approved_at: datetime | None
    disbursed_at: datetime | None
    due_date: datetime | None
    repaid_at: datetime | None
    defaulted_at: datetime | None
    score_profile_id: UUID | None