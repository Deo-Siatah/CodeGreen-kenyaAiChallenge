from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FarmActivityReading:
    ndvi_value: float | None
    cultivation_continuity_score: float | None
    observation_date: date
    source: str


class FarmActivityProvider(ABC):
    @abstractmethod
    async def fetch_latest(
        self, latitude: float, longitude: float
    ) -> FarmActivityReading | None:
        """Fetch the latest activity reading for coordinates."""
        raise NotImplementedError


class NullFarmActivityProvider(FarmActivityProvider):
    async def fetch_latest(
        self, latitude: float, longitude: float
    ) -> FarmActivityReading | None:
        logger.debug(
            "Farm activity provider is not configured; skipping coordinates "
            "latitude=%s longitude=%s",
            latitude,
            longitude,
        )
        return None
