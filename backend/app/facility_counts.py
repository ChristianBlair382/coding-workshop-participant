"""Helpers for keeping facility aggregate counts in sync with child records."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.orm_models import Building, Floor, Seat


async def sync_building_floor_count(db: AsyncSession, building_id: int) -> None:
    """Set a building's floor count to its number of persisted floors."""
    building = await db.get(Building, building_id)
    if building is None:
        return
    floor_count = await db.scalar(
        select(func.count(Floor.id)).where(Floor.building_id == building_id)
    )
    building.floor_count = floor_count or 0


async def sync_floor_seat_count(db: AsyncSession, floor_id: int) -> None:
    """Set a floor's seat count to its number of persisted seats."""
    floor = await db.get(Floor, floor_id)
    if floor is None:
        return
    seat_count = await db.scalar(
        select(func.count(Seat.id)).where(Seat.floor_id == floor_id)
    )
    floor.seat_count = seat_count or 0
