import contextlib
import sys
import uuid
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.database import _asyncpg_url, _ssl_connect_args
from models.audit import AuditLog
from models.signals import FarmActivitySignal
from services.farmer_service import FarmerService
from services.farm_activity.provider import (
    FarmActivityProvider,
    FarmActivityReading,
    NullFarmActivityProvider,
)

sys.path.append(str(Path(__file__).parent.parent.parent / "integration"))
from tests.integration.db_target import TEST_URL, skip_marker

pytestmark = skip_marker()

_URL = TEST_URL or ""


@contextlib.asynccontextmanager
async def db():
    engine = create_async_engine(
        _asyncpg_url(_URL, "TEST_DATABASE_URL_DIRECT"),
        poolclass=pool.NullPool,
        connect_args=_ssl_connect_args(_URL, "TEST_DATABASE_URL_DIRECT"),
    )
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


def farmer_data() -> dict:
    tag = uuid.uuid4().hex
    return {
        "full_name": "Test Farmer",
        "national_id": f"NA-{tag}",
        "phone": f"+2547{tag[:8]}",
        "gender": "female",
        "location": "Testville",
    }


def farm_data() -> dict:
    return {
        "acreage": 2.5,
        "latitude": -1.286389,
        "longitude": 36.817223,
    }


async def test_create_farmer_round_trips_and_writes_audit_log():
    async with db() as Session:
        async with Session() as session:
            service = FarmerService()
            farmer = await service.create_farmer(session, farmer_data())

            loaded = await service.get_farmer(session, farmer.id)
            assert loaded is not None
            assert loaded.id == farmer.id
            assert loaded.full_name == farmer.full_name

            audit = (
                await session.execute(
                    select(AuditLog).where(
                        AuditLog.entity_type == "farmer",
                        AuditLog.entity_id == farmer.id,
                        AuditLog.action == "farmer_created",
                    )
                )
            ).scalar_one()
            assert audit.actor_type == "officer"
            await session.rollback()


async def test_create_farm_with_null_provider_creates_no_activity_signal():
    async with db() as Session:
        async with Session() as session:
            farmer = await FarmerService().create_farmer(session, farmer_data())
            farm = await FarmerService().create_farm(
                session, farmer.id, farm_data()
            )

            signals = (
                await session.execute(
                    select(FarmActivitySignal).where(
                        FarmActivitySignal.farm_id == farm.id
                    )
                )
            ).scalars().all()
            assert signals == []
            await session.rollback()


class FakeFarmActivityProvider(FarmActivityProvider):
    async def fetch_latest(
        self, latitude: float, longitude: float
    ) -> FarmActivityReading | None:
        return FarmActivityReading(
            ndvi_value=0.72,
            cultivation_continuity_score=88.0,
            observation_date=date(2026, 9, 30),
            source="fake_provider",
        )


async def test_create_farm_with_reading_creates_activity_signal():
    async with db() as Session:
        async with Session() as session:
            farmer_service = FarmerService(
                farm_activity_provider=FakeFarmActivityProvider()
            )
            farmer = await farmer_service.create_farmer(session, farmer_data())
            farm = await farmer_service.create_farm(
                session, farmer.id, farm_data()
            )

            signal = (
                await session.execute(
                    select(FarmActivitySignal).where(
                        FarmActivitySignal.farm_id == farm.id
                    )
                )
            ).scalar_one()
            assert signal.ndvi_value == 0.72
            assert signal.cultivation_continuity_score == 88.0
            assert signal.observation_date == date(2026, 9, 30)
            assert signal.source == "fake_provider"
            await session.rollback()


@pytest.mark.parametrize(
    ("provider", "captured"),
    [(NullFarmActivityProvider(), False), (FakeFarmActivityProvider(), True)],
)
async def test_create_farm_audit_records_activity_capture(provider, captured):
    async with db() as Session:
        async with Session() as session:
            farmer_service = FarmerService(farm_activity_provider=provider)
            farmer = await farmer_service.create_farmer(session, farmer_data())
            farm = await farmer_service.create_farm(
                session, farmer.id, farm_data()
            )

            audit = (
                await session.execute(
                    select(AuditLog).where(
                        AuditLog.entity_type == "farm",
                        AuditLog.entity_id == farm.id,
                        AuditLog.action == "farm_created",
                    )
                )
            ).scalar_one()
            assert audit.details == {"activity_data_captured": captured}
            await session.rollback()
