from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_permission
from app.facility_counts import sync_floor_seat_count
from app.orm_models import Floor, Seat, User
from app.schemas import Seat_Bulk_Create, Seat_Create, Seat_Read, Seat_Update

router = APIRouter(prefix="/seats", tags=["seats"])


async def _next_seat_ids(
    db: AsyncSession,
    floor: Floor,
    count: int,
) -> list[str]:
    """Generate unused seat identifiers matching the seeded floor convention."""
    prefix = f"F{floor.floor_id}-"
    existing_ids = (
        await db.scalars(select(Seat.seat_id).where(Seat.floor_id == floor.id))
    ).all()
    used_numbers = set()
    for seat_id in existing_ids:
        suffix = seat_id.removeprefix(prefix)
        if seat_id.startswith(prefix) and suffix.isdigit():
            used_numbers.add(int(suffix))

    seat_ids: list[str] = []
    next_number = 1
    while len(seat_ids) < count:
        if next_number not in used_numbers:
            seat_ids.append(f"{prefix}{next_number:02}")
        next_number += 1
    return seat_ids


async def _validate_user_assignments(
    db: AsyncSession,
    user_ids: list[int],
    seat_id: int | None = None,
) -> None:
    """Ensure each requested occupant exists and is not assigned to another seat."""
    if len(user_ids) != len(set(user_ids)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user cannot be assigned to more than one new seat.",
        )
    if not user_ids:
        return

    existing_users = set(
        (
            await db.scalars(select(User.id).where(User.id.in_(user_ids)))
        ).all()
    )
    if existing_users != set(user_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="One or more selected users do not exist.",
        )

    assigned_seats = select(Seat.id).where(Seat.occupied_by.in_(user_ids))
    if seat_id is not None:
        assigned_seats = assigned_seats.where(Seat.id != seat_id)
    if await db.scalar(assigned_seats.limit(1)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="One or more selected users are already assigned to a seat.",
        )


@router.get("", response_model=list[Seat_Read])
async def list_seats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("seats:read")),
) -> list[Seat]:
    """List all seats."""
    result = await db.scalars(select(Seat).order_by(Seat.id))
    return list(result.all())


@router.get("/{seat_id}", response_model=Seat_Read)
async def get_seat(
    seat_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("seats:read")),
) -> Seat:
    """Get a seat by ID."""
    seat = await db.get(Seat, seat_id)
    if seat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seat not found.")
    return seat


@router.post("", response_model=Seat_Read, status_code=status.HTTP_201_CREATED)
async def create_seat(
    payload: Seat_Create,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("seats:create")),
) -> Seat:
    """Create a seat with a floor-scoped identifier."""
    floor = await db.get(Floor, payload.floor_id)
    if floor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor not found.")
    await _validate_user_assignments(
        db,
        [payload.occupied_by] if payload.occupied_by is not None else [],
    )
    seat = Seat(
        seat_id=(await _next_seat_ids(db, floor, 1))[0],
        occupied_by=payload.occupied_by,
        floor_id=payload.floor_id,
    )
    db.add(seat)
    await db.flush()
    await sync_floor_seat_count(db, seat.floor_id)
    await db.commit()
    await db.refresh(seat)
    return seat


@router.post(
    "/floors/{floor_id}/bulk",
    response_model=list[Seat_Read],
    status_code=status.HTTP_201_CREATED,
)
async def create_seats(
    floor_id: int,
    payload: Seat_Bulk_Create,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("seats:create")),
) -> list[Seat]:
    """Create multiple consecutively numbered seats on one floor."""
    floor = await db.get(Floor, floor_id)
    if floor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor not found.")

    user_ids = [user_id for user_id in payload.occupied_by if user_id is not None]
    await _validate_user_assignments(db, user_ids)

    seat_ids = await _next_seat_ids(db, floor, len(payload.occupied_by))
    new_seats = [
        Seat(
            seat_id=seat_id,
            occupied_by=user_id,
            floor_id=floor.id,
        )
        for seat_id, user_id in zip(seat_ids, payload.occupied_by)
    ]
    db.add_all(new_seats)
    await db.flush()
    await sync_floor_seat_count(db, floor.id)
    await db.commit()
    for seat in new_seats:
        await db.refresh(seat)
    return new_seats


@router.patch("/{seat_id}", response_model=Seat_Read)
async def update_seat(
    seat_id: int,
    payload: Seat_Update,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("seats:update")),
) -> Seat:
    """Update a seat."""
    seat = await db.get(Seat, seat_id)
    if seat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seat not found.")
    old_floor_id = seat.floor_id
    changes = payload.model_dump(exclude_unset=True)
    if "occupied_by" in changes and changes["occupied_by"] is not None:
        await _validate_user_assignments(
            db,
            [changes["occupied_by"]],
            seat_id=seat.id,
        )
    for field, value in changes.items():
        setattr(seat, field, value)
    await db.flush()
    await sync_floor_seat_count(db, old_floor_id)
    if seat.floor_id != old_floor_id:
        await sync_floor_seat_count(db, seat.floor_id)
    await db.commit()
    await db.refresh(seat)
    return seat


@router.delete("/{seat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_seat(
    seat_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("seats:delete")),
) -> Response:
    """Delete a seat."""
    seat = await db.get(Seat, seat_id)
    if seat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seat not found.")
    floor_id = seat.floor_id
    await db.delete(seat)
    await db.flush()
    await sync_floor_seat_count(db, floor_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
