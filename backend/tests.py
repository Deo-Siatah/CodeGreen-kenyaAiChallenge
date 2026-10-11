# nuke_and_rebuild.py — run with: uv run python nuke_and_rebuild.py
import asyncio
from core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from core.database import _asyncpg_url, _ssl_connect_args

async def main():
    host = settings.DATABASE_URL_DIRECT.split('@')[1].split('/')[0]
    print(f"About to WIPE and rebuild: {host}")
    confirm = input("Type the host name exactly to confirm: ")
    if confirm != host:
        print("Mismatch — aborted, nothing touched.")
        return

    engine = create_async_engine(
        _asyncpg_url(settings.DATABASE_URL_DIRECT),
        connect_args=_ssl_connect_args(settings.DATABASE_URL_DIRECT),
    )
    async with engine.begin() as conn:
        await conn.exec_driver_sql("DROP SCHEMA public CASCADE")
        await conn.exec_driver_sql("CREATE SCHEMA public")
    await engine.dispose()
    print("Schema wiped. Now run: uv run alembic upgrade head")

asyncio.run(main())