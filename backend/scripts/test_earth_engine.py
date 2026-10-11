"""Manual diagnostic: python scripts/test_earth_engine.py LATITUDE LONGITUDE."""

from __future__ import annotations

import argparse
import asyncio

from services.farm_activity.earth_engine_provider import (
    EarthEngineFarmActivityProvider,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query Sentinel-2 farm activity")
    parser.add_argument("latitude", type=float)
    parser.add_argument("longitude", type=float)
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    provider = EarthEngineFarmActivityProvider()
    reading = await provider.fetch_latest(args.latitude, args.longitude)
    print(reading)


if __name__ == "__main__":
    asyncio.run(main())
