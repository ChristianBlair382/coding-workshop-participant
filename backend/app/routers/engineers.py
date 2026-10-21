from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_permission
from app.orm_models import Engineer, User
from app.schemas import Engineer_Create, Engineer_Read, Engineer_Update

router = APIRouter(prefix="/engineers", tags=["engineers"])


@router.get("/me", response_model=Engineer_Read)
async def get_my_engineer_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("engineers:read")),
) -> Engineer:
    """Get the authenticated engineer's profile."""
    engineer = await db.scalar(
        select(Engineer).where(Engineer.user_id == current_user.id)
    )
    if engineer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engineer profile not found.")
    return engineer


@router.get("", response_model=list[Engineer_Read])
async def list_engineers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("engineers:read")),
) -> list[Engineer]:
    """List all engineers."""
    result = await db.scalars(select(Engineer).order_by(Engineer.id))
    return list(result.all())


@router.get("/{engineer_id}", response_model=Engineer_Read)
async def get_engineer(
    engineer_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("engineers:read")),
) -> Engineer:
    """Get an engineer by ID."""
    engineer = await db.get(Engineer, engineer_id)
    if engineer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engineer not found.")
    return engineer


@router.post("", response_model=Engineer_Read, status_code=status.HTTP_201_CREATED)
async def create_engineer(
    payload: Engineer_Create,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("engineers:create")),
) -> Engineer:
    """Create an engineer profile."""
    engineer = Engineer(**payload.model_dump())
    db.add(engineer)
    await db.commit()
    await db.refresh(engineer)
    return engineer


@router.patch("/{engineer_id}", response_model=Engineer_Read)
async def update_engineer(
    engineer_id: int,
    payload: Engineer_Update,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("engineers:update")),
) -> Engineer:
    """Update an engineer profile."""
    engineer = await db.get(Engineer, engineer_id)
    if engineer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engineer not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(engineer, field, value)
    await db.commit()
    await db.refresh(engineer)
    return engineer


@router.delete("/{engineer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_engineer(
    engineer_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("engineers:delete")),
) -> Response:
    """Delete an engineer profile."""
    engineer = await db.get(Engineer, engineer_id)
    if engineer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engineer not found.")
    await db.delete(engineer)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
