"""Earth Engine farm-activity provider.

This provider is intentionally not covered by automated integration tests
against the live Earth Engine API. Live calls are slow, network-dependent, and
consume project quota; manual verification through scripts/test_earth_engine.py
is the intended check for a real farm location.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ee

from core.config import settings
from services.farm_activity.provider import FarmActivityProvider, FarmActivityReading

# Tunable acquisition policy. These values are deliberately named constants so
# changing spatial coverage or image quality does not require editing query code.
BUFFER_METERS = 50
MAX_CLOUD_PERCENT = 20
LOOKBACK_DAYS = 90
CONTINUITY_LOOKBACK_DAYS = 180
VEGETATION_PRESENCE_NDVI = 0.30
RED_BAND = "B4"
NIR_BAND = "B8"
COLLECTION_ID = "COPERNICUS/S2_SR_HARMONIZED"
CLOUD_PROPERTY = "CLOUDY_PIXEL_PERCENTAGE"
REDUCE_SCALE_METERS = 10


class EarthEngineAuthenticationError(RuntimeError):
    """Raised when the configured Earth Engine credentials cannot initialize."""


class EarthEngineFarmActivityProvider(FarmActivityProvider):
    """Read recent Sentinel-2 vegetation activity around a farm coordinate."""

    def __init__(self, service_account_json: str | None = None) -> None:
        key_path = Path(
            service_account_json or settings.EARTH_ENGINE_SERVICE_ACCOUNT_JSON
        )
        try:
            with key_path.open(encoding="utf-8") as key_file:
                service_account_email = json.load(key_file)["client_email"]
            credentials = ee.ServiceAccountCredentials(
                service_account_email, key_file=str(key_path)
            )
            ee.Initialize(credentials)
        except Exception as exc:
            raise EarthEngineAuthenticationError(
                "Earth Engine authentication failed. Check "
                "EARTH_ENGINE_SERVICE_ACCOUNT_JSON and the Earth Engine project "
                "configuration."
            ) from exc

    async def fetch_latest(
        self, latitude: float, longitude: float
    ) -> FarmActivityReading | None:
        return await asyncio.to_thread(self._fetch_latest_sync, latitude, longitude)

    def _fetch_latest_sync(
        self, latitude: float, longitude: float
    ) -> FarmActivityReading | None:
        now = datetime.now(timezone.utc)
        point = ee.Geometry.Point([longitude, latitude])
        region = point.buffer(BUFFER_METERS)
        recent_start = now - timedelta(days=LOOKBACK_DAYS)
        continuity_start = now - timedelta(days=CONTINUITY_LOOKBACK_DAYS)

        recent_images = (
            ee.ImageCollection(COLLECTION_ID)
            .filterDate(recent_start.isoformat(), now.isoformat())
            .filter(ee.Filter.lte(CLOUD_PROPERTY, MAX_CLOUD_PERCENT))
            .filterBounds(region)
            .sort("system:time_start", False)
        )
        if recent_images.size().getInfo() == 0:
            return None

        latest = ee.Image(recent_images.first())
        latest_ndvi = latest.normalizedDifference([NIR_BAND, RED_BAND]).rename("ndvi")
        latest_value = latest_ndvi.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=REDUCE_SCALE_METERS,
            bestEffort=True,
        ).get("ndvi").getInfo()
        latest_timestamp = latest.get("system:time_start").getInfo()
        observation_date = datetime.fromtimestamp(
            latest_timestamp / 1000, tz=timezone.utc
        ).date()

        continuity_images = (
            ee.ImageCollection(COLLECTION_ID)
            .filterDate(continuity_start.isoformat(), now.isoformat())
            .filter(ee.Filter.lte(CLOUD_PROPERTY, MAX_CLOUD_PERCENT))
            .filterBounds(region)
        )
        if continuity_images.size().getInfo() == 0:
            continuity_score = 0.0
        else:
            vegetation_fraction = (
                continuity_images
                .map(self._vegetation_presence_image)
                .mean()
                .reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=region,
                    scale=REDUCE_SCALE_METERS,
                    bestEffort=True,
                )
                .get("vegetation_presence")
                .getInfo()
            )
            continuity_score = float(vegetation_fraction or 0.0) * 100

        return FarmActivityReading(
            ndvi_value=float(latest_value) if latest_value is not None else None,
            cultivation_continuity_score=max(0.0, min(100.0, continuity_score)),
            observation_date=observation_date,
            source="sentinel2",
        )

    @staticmethod
    def _vegetation_presence_image(image):
        ndvi = ee.Image(image).normalizedDifference([NIR_BAND, RED_BAND])
        return ndvi.gt(VEGETATION_PRESENCE_NDVI).rename("vegetation_presence")
