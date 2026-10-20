# Run with: python -m services.create_tables
# From: backend/ with venv active

import asyncio
from app.database import engine
from app.orm_models import Base

async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(create_tables())