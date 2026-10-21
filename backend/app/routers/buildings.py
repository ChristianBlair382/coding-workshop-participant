from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_permission
from app.facility_counts import sync_building_floor_count
from app.orm_models import Building, Floor, User
from app.schemas import Building_Create, Building_Read, Building_Update

router = APIRouter(prefix="/buildings", tags=["buildings"])

# GET ROUTERS

@router.get("", response_model=list[Building_Read])
async def list_buildings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("buildings:read")),
) -> list[Building]:
    """List all buildings."""
    result = await db.scalars(select(Building).order_by(Building.id))
    return list(result.all())

@router.get("/{building_id}", response_model=Building_Read)
async def get_building(
    building_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("buildings:read")),
) -> Building:
    """Get a building by ID."""
    building = await db.get(Building, building_id)
    if building is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found.")
    return building

# POST ROUTERS

@router.post("", response_model=Building_Read, status_code=status.HTTP_201_CREATED)
async def create_building(
    payload: Building_Create,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("buildings:create")),
) -> Building:
    """Create a building."""
    building = Building(
        name=payload.name,
        location=payload.location,
        floor_count=0,
    )
    db.add(building)
    await db.flush()
    db.add_all(
        Floor(
            floor_id=str(floor_number),
            seat_count=0,
            building_id=building.id,
        )
        for floor_number in range(1, payload.floor_count + 1)
    )
    await db.flush()
    await sync_building_floor_count(db, building.id)
    await db.commit()
    await db.refresh(building)
    return building

# PATCH ROUTERS

@router.patch("/{building_id}", response_model=Building_Read)
async def update_building(
    building_id: int,
    payload: Building_Update,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("buildings:update")),
) -> Building:
    """Update a building."""
    building = await db.get(Building, building_id)
    if building is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(building, field, value)
    await db.flush()
    await sync_building_floor_count(db, building_id)
    await db.commit()
    await db.refresh(building)
    return building

# DELETE ROUTERS

@router.delete("/{building_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_building(
    building_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("buildings:delete")),
) -> Response:
    """Delete a building."""
    building = await db.get(Building, building_id)
    if building is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found.")
    await db.delete(building)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
