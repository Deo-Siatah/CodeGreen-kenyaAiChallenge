from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.farmer import Farm, Farmer
from models.links import (
    FarmerInstitutionLink,
    FarmerMarketActorLink,
    FarmerSocialGroupLink,
    FarmerTrustSourceLink,
)
from models.loan import Loan
from models.scoring import ScoreComponent, ScoreProfile
from models.trust import MarketActor, SocialGroup, TrustSource
from models.verification import VerificationParticipant, VerificationSession
from services.stats_service import (
    ComponentRow,
    FarmerRow,
    LoanRow,
    ScoreRow,
    StatsSnapshot,
)


class StatsRepository:


    async def _count(self, session: AsyncSession, model) -> int:
        statement = select(func.count()).select_from(model)
        return int((await session.execute(statement)).scalar_one())

    async def snapshot(self, session: AsyncSession) -> StatsSnapshot:
        farmer_rows = (
            await session.execute(
                select(
                    Farmer.id,
                    Farmer.full_name,
                    Farmer.county,
                    Farmer.gender,
                    Farmer.created_at,
                ).order_by(Farmer.created_at.desc(), Farmer.id)
            )
        ).all()

        score_rows = (
            await session.execute(
                select(
                    ScoreProfile.farmer_id,
                    ScoreProfile.final_score,
                    ScoreProfile.character_score,
                    ScoreProfile.capacity_score,
                    ScoreProfile.decision,
                    ScoreProfile.recommended_amount,
                ).where(ScoreProfile.is_current.is_(True))
            )
        ).all()

        component_rows = (
            await session.execute(
                select(
                    ScoreComponent.component_name,
                    ScoreComponent.contribution,
                )
                .join(
                    ScoreProfile,
                    ScoreComponent.score_profile_id == ScoreProfile.id,
                )
                .where(ScoreProfile.is_current.is_(True))
            )
        ).all()

        loan_rows = (
            await session.execute(
                select(
                    Loan.id,
                    Loan.farmer_id,
                    Loan.amount,
                    Loan.status,
                    Loan.applied_at,
                ).order_by(Loan.applied_at.desc(), Loan.id)
            )
        ).all()

        farm_rows = (
            await session.execute(
                select(Farm.farmer_id, Farm.acreage).order_by(
                    Farm.created_at.asc(), Farm.id
                )
            )
        ).all()

        acreage_by_farmer: dict[UUID, float | None] = {}
        for farmer_id, acreage in farm_rows:
            if acreage is not None:
                acreage_by_farmer.setdefault(farmer_id, float(acreage))
            else:
                acreage_by_farmer.setdefault(farmer_id, None)

        links = 0
        for model in (
            FarmerTrustSourceLink,
            FarmerInstitutionLink,
            FarmerSocialGroupLink,
            FarmerMarketActorLink,
        ):
            links += await self._count(session, model)

        sessions = await self._count(session, VerificationSession)
        completed_sessions = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(VerificationSession)
                    .where(VerificationSession.status == "completed")
                )
            ).scalar_one()
        )
        participants = await self._count(session, VerificationParticipant)
        responded_participants = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(VerificationParticipant)
                    .where(VerificationParticipant.responded_at.is_not(None))
                )
            ).scalar_one()
        )

        return StatsSnapshot(
            farmers=[
                FarmerRow(
                    id=row.id,
                    full_name=row.full_name,
                    county=row.county,
                    gender=row.gender,
                    created_at=row.created_at,
                )
                for row in farmer_rows
            ],
            scores=[
                ScoreRow(
                    farmer_id=row.farmer_id,
                    final_score=float(row.final_score),
                    character_score=float(row.character_score),
                    capacity_score=(
                        float(row.capacity_score)
                        if row.capacity_score is not None
                        else None
                    ),
                    decision=row.decision,
                    recommended_amount=(
                        float(row.recommended_amount)
                        if row.recommended_amount is not None
                        else None
                    ),
                )
                for row in score_rows
            ],
            components=[
                ComponentRow(
                    component_name=row.component_name,
                    contribution=(
                        float(row.contribution) if row.contribution is not None else None
                    ),
                )
                for row in component_rows
            ],
            loans=[
                LoanRow(
                    id=row.id,
                    farmer_id=row.farmer_id,
                    amount=float(row.amount),
                    status=row.status,
                    applied_at=row.applied_at,
                )
                for row in loan_rows
            ],
            acreage_by_farmer=acreage_by_farmer,
            trust_sources=await self._count(session, TrustSource),
            market_actors=await self._count(session, MarketActor),
            social_groups=await self._count(session, SocialGroup),
            links=links,
            sessions=sessions,
            completed_sessions=completed_sessions,
            participants=participants,
            responded_participants=responded_participants,
        )
