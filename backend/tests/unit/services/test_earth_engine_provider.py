from datetime import date
from types import SimpleNamespace

import pytest

import services.farm_activity.earth_engine_provider as provider_module
from services.farm_activity.earth_engine_provider import (
    EarthEngineFarmActivityProvider,
)


class Value:
    def __init__(self, value):
        self.value = value

    def getInfo(self):
        return self.value


class FakeImage:
    def __init__(self, ndvi=0.6, timestamp=1_759_276_800_000):
        self.ndvi = ndvi
        self.timestamp = timestamp

    def normalizedDifference(self, bands):
        return self

    def rename(self, name):
        return self

    def reduceRegion(self, **kwargs):
        return FakeRegionResult(self.ndvi)

    def get(self, name):
        return Value(self.timestamp)

    def gt(self, threshold):
        return self


class FakeRegionResult:
    def __init__(self, value):
        self.value = value

    def get(self, name):
        return Value(self.value)


class FakeCollection:
    def __init__(self, count):
        self.count = count

    def filterDate(self, start, end):
        return self

    def filter(self, condition):
        return self

    def filterBounds(self, region):
        return self

    def sort(self, field, descending):
        return self

    def size(self):
        return Value(self.count)

    def first(self):
        return FakeImage()

    def map(self, function):
        function(FakeImage())
        return self

    def mean(self):
        return FakeImage(ndvi=0.65)


class FakePoint:
    def buffer(self, metres):
        return self


class FakeEE:
    def __init__(self, count):
        self.count = count
        self.Geometry = SimpleNamespace(Point=lambda coordinates: FakePoint())
        self.Filter = SimpleNamespace(lte=lambda name, value: (name, value))
        self.Reducer = SimpleNamespace(mean=lambda: "mean")

    def ImageCollection(self, collection_id):
        return FakeCollection(self.count)

    def Image(self, image):
        return image


@pytest.mark.asyncio
async def test_empty_cloud_filtered_collection_returns_none(monkeypatch):
    provider = EarthEngineFarmActivityProvider.__new__(EarthEngineFarmActivityProvider)
    monkeypatch.setattr(provider_module, "ee", FakeEE(count=0))

    result = await provider.fetch_latest(-1.28, 36.82)

    assert result is None


@pytest.mark.asyncio
async def test_non_empty_collection_returns_bounded_reading(monkeypatch):
    provider = EarthEngineFarmActivityProvider.__new__(EarthEngineFarmActivityProvider)
    monkeypatch.setattr(provider_module, "ee", FakeEE(count=2))

    result = await provider.fetch_latest(-1.28, 36.82)

    assert result is not None
    assert result.ndvi_value == 0.6
    assert 0 <= result.cultivation_continuity_score <= 100
    assert result.observation_date == date(2025, 10, 1)
    assert result.source == "sentinel2"
