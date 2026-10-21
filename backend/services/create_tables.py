# Run with: python -m services.create_tables
# From: backend/ with venv active

import asyncio

from sqlalchemy import inspect, text

from app.database import engine
from app.orm_models import Base

async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        existing_columns = await conn.run_sync(
            lambda sync_conn: {
                column["name"]
                for column in inspect(sync_conn).get_columns("incident_tickets")
            }
        )
        timestamp_type = (
            "TIMESTAMP WITH TIME ZONE"
            if conn.dialect.name == "postgresql"
            else "DATETIME"
        )
        for column_name in (
            "created_at",
            "acknowledged_at",
            "assigned_at",
            "completed_at",
        ):
            if column_name not in existing_columns:
                await conn.execute(
                    text(
                        f"ALTER TABLE incident_tickets "
                        f"ADD COLUMN {column_name} {timestamp_type}"
                    )
                )
        if conn.dialect.name == "postgresql":
            await conn.execute(
                text(
                    "ALTER TABLE incident_tickets "
                    "ALTER COLUMN assigned_engineer_id DROP NOT NULL"
                )
            )

if __name__ == "__main__":
    asyncio.run(create_tables())