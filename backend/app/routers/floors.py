from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_permission
from app.facility_counts import sync_building_floor_count, sync_floor_seat_count
from app.orm_models import Floor, User
from app.schemas import Floor_Create, Floor_Read, Floor_Update

router = APIRouter(prefix="/floors", tags=["floors"])


@router.get("", response_model=list[Floor_Read])
async def list_floors(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("floors:read")),
) -> list[Floor]:
    """List all floors."""
    result = await db.scalars(select(Floor).order_by(Floor.id))
    return list(result.all())


@router.get("/{floor_id}", response_model=Floor_Read)
async def get_floor(
    floor_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("floors:read")),
) -> Floor:
    """Get a floor by ID."""
    floor = await db.get(Floor, floor_id)
    if floor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor not found.")
    return floor


@router.post("", response_model=Floor_Read, status_code=status.HTTP_201_CREATED)
async def create_floor(
    payload: Floor_Create,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("floors:create")),
) -> Floor:
    """Create a floor."""
    floor = Floor(
        floor_id=payload.floor_id,
        seat_count=0,
        building_id=payload.building_id,
    )
    db.add(floor)
    await db.flush()
    await sync_building_floor_count(db, floor.building_id)
    await db.commit()
    await db.refresh(floor)
    return floor


@router.patch("/{floor_id}", response_model=Floor_Read)
async def update_floor(
    floor_id: int,
    payload: Floor_Update,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("floors:update")),
) -> Floor:
    """Update a floor."""
    floor = await db.get(Floor, floor_id)
    if floor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor not found.")
    old_building_id = floor.building_id
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(floor, field, value)
    await db.flush()
    await sync_floor_seat_count(db, floor.id)
    await sync_building_floor_count(db, old_building_id)
    if floor.building_id != old_building_id:
        await sync_building_floor_count(db, floor.building_id)
    await db.commit()
    await db.refresh(floor)
    return floor


@router.delete("/{floor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_floor(
    floor_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("floors:delete")),
) -> Response:
    """Delete a floor."""
    floor = await db.get(Floor, floor_id)
    if floor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor not found.")
    building_id = floor.building_id
    await db.delete(floor)
    await db.flush()
    await sync_building_floor_count(db, building_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
