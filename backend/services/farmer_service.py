from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.farmer import Farm, Farmer
from repositories.farm_activity_repository import FarmActivityRepository
from repositories.farmer_repository import FarmerRepository
from services.audit_service import AuditService
from services.farm_activity.provider import (
    FarmActivityProvider,
    NullFarmActivityProvider,
)


class DuplicateFarmerError(Exception):
    """Raised when trying to create a farmer with duplicate national_id or phone."""
    pass


def build_farmer_service() -> "FarmerService":
    """Construct FarmerService from the configured activity-provider flag."""
    if settings.FARM_ACTIVITY_PROVIDER == "earth_engine":
        from services.farm_activity.earth_engine_provider import (
            EarthEngineFarmActivityProvider,
        )

        provider = EarthEngineFarmActivityProvider()
    else:
        provider = NullFarmActivityProvider()
    return FarmerService(farm_activity_provider=provider)


class FarmerService:
    def __init__(
        self,
        farm_activity_provider: FarmActivityProvider = NullFarmActivityProvider(),
        farmer_repository: FarmerRepository | None = None,
        farm_activity_repository: FarmActivityRepository | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.farm_activity_provider = farm_activity_provider
        self.repository = farmer_repository or FarmerRepository()
        self.farm_activity_repository = (
            farm_activity_repository or FarmActivityRepository()
        )
        self.audit_service = audit_service or AuditService()

    async def create_farmer(
        self, session: AsyncSession, farmer_data: dict[str, Any]
    ) -> Farmer:
        try:
            farmer = await self.repository.create_farmer(session, farmer_data)
            await session.flush()
            await self.audit_service.write_log(
                session,
                actor_type="officer",
                actor_id=None,
                action="farmer_created",
                entity_type="farmer",
                entity_id=farmer.id,
            )
        except IntegrityError as exc:
            raise DuplicateFarmerError("Farmer with this national ID or phone already exists") from exc
        return farmer

    async def create_farm(
        self,
        session: AsyncSession,
        farmer_id: uuid.UUID | str,
        farm_data: dict[str, Any],
    ) -> Farm:
        farm_values = dict(farm_data)
        farm_values["farmer_id"] = farmer_id
        farm = await self.repository.create_farm(session, farm_values)
        await session.flush()

        reading = await self.farm_activity_provider.fetch_latest(
            farm.latitude, farm.longitude
        )
        captured = reading is not None
        if reading is not None:
            await self.farm_activity_repository.create_farm_activity_signal(
                session,
                farm_id=farm.id,
                ndvi_value=reading.ndvi_value,
                cultivation_continuity_score=reading.cultivation_continuity_score,
                observation_date=reading.observation_date,
                source=reading.source,
            )

        await self.audit_service.write_log(
            session,
            actor_type="officer",
            actor_id=None,
            action="farm_created",
            entity_type="farm",
            entity_id=farm.id,
            details={"activity_data_captured": captured},
        )
        return farm

    async def get_farmer(
        self, session: AsyncSession, farmer_id: uuid.UUID | str
    ) -> Farmer | None:
        return await self.repository.get_farmer(session, farmer_id)