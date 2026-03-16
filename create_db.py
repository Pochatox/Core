# flake8-in-file-ignores: noqa: WPS102

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.sqlalchemy.models import Base

load_dotenv(Path(__file__).parent / '.env')


async def main() -> None:
    engine = create_async_engine(
        url=os.getenv('DATABASE_URL'),  # type: ignore
        echo=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

asyncio.run(main())
