from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from repositories.stats_repository import StatsRepository
from schemas.stats import StatsOverviewResponse
from services.stats_service import build_overview

router = APIRouter(prefix="/api", tags=["Stats"])


@router.get("/stats/overview", response_model=StatsOverviewResponse)
async def get_stats_overview(
    session: AsyncSession = Depends(get_db_session),
) -> StatsOverviewResponse:
    snapshot = await StatsRepository().snapshot(session)
    return build_overview(snapshot)
