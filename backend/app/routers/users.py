from fastapi import APIRouter, HTTPException, status, Depends, Response, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, require_permission
from app.orm_models import Permission, RolePermission, User, USER_ROLE
from app.orm_models import Seat
from app.routers.auth import register_new_user
from app.schemas import (
    Role_Permissions_Read,
    User_Permissions_Read,
    User_Read,
    User_Update,
)

router = APIRouter(prefix="/users", tags=["users"])

# GET Routers

@router.get("/me/permissions", response_model=User_Permissions_Read)
async def get_my_permissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User_Permissions_Read:
    result = await db.execute(
        select(Permission)
        .join(RolePermission)
        .where(RolePermission.role == current_user.role.value)
        .order_by(Permission.name)
    )
    return User_Permissions_Read(
        role=current_user.role,
        permissions=result.scalars().all(),
    )

@router.get(
    "/roles-permissions",
    response_model=list[Role_Permissions_Read],
)
async def list_role_permissions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("users:read")),
) -> list[Role_Permissions_Read]:
    result = await db.execute(
        select(RolePermission.role, Permission)
        .join(Permission)
        .order_by(RolePermission.role, Permission.name)
    )
    permissions_by_role: dict[str, list[Permission]] = {
        role.value: [] for role in USER_ROLE
    }
    for role, permission in result:
        permissions_by_role[role].append(permission)

    return [
        Role_Permissions_Read(
            role=role,
            permissions=permissions_by_role[role.value],
        )
        for role in USER_ROLE
    ]

@router.get("", response_model=list[User_Read])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("users:read"))
):
    db_command = select(User).order_by(User.id)

    output = await db.execute(db_command)

    return list(output.scalars().all())


@router.get("/seat-assignment-options", response_model=list[User_Read])
async def list_seat_assignment_options(
    query: str = Query(default="", max_length=50),
    include_user_id: int | None = Query(default=None, gt=0),
    include_user_ids: list[int] = Query(default=[]),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("users:read")),
) -> list[User]:
    """Search unassigned users for seat assignment without loading the full user table."""
    assigned_user_ids = select(Seat.occupied_by).where(Seat.occupied_by.is_not(None))
    included_ids = set(include_user_ids)
    if include_user_id is not None:
        included_ids.add(include_user_id)
    included_users = (
        list(
            (
                await db.scalars(
                    select(User).where(User.id.in_(included_ids))
                )
            ).all()
        )
        if included_ids
        else []
    )
    available_users = (
        list(
            (
                await db.scalars(
                    select(User)
                    .where(
                        User.username.ilike(f"%{query.strip()}%"),
                        ~User.id.in_(assigned_user_ids),
                    )
                    .order_by(User.username)
                    .limit(25)
                )
            ).all()
        )
        if len(query.strip()) >= 2
        else []
    )
    users_by_id = {user.id: user for user in included_users}
    users_by_id.update({user.id: user for user in available_users})
    return list(users_by_id.values())


@router.get("/dashboard-counts")
async def get_dashboard_user_counts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    """Return aggregate user counts without exposing individual user records."""
    employee_count = await db.scalar(
        select(func.count(User.id)).where(User.role == USER_ROLE.EMP)
    )
    engineer_count = await db.scalar(
        select(func.count(User.id)).where(User.role == USER_ROLE.ENG)
    )
    counts = {
        "employee_count": employee_count or 0,
        "engineer_count": engineer_count or 0,
    }
    if current_user.role == USER_ROLE.FA:
        facility_admin_count = await db.scalar(
            select(func.count(User.id)).where(User.role == USER_ROLE.FA)
        )
        counts["facility_admin_count"] = facility_admin_count or 0
    return counts


@router.get("/{user_id}", response_model=User_Read)
async def find_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("users:read"))
):
    target_user = await db.get(User, user_id)

    if (not target_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' does not exist."
        )
    return target_user

# PATCH Routers

@router.patch("/{user_id}", response_model=User_Read)
async def update_user(
    user_id: int,
    payload: User_Update,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("users:update"))
):
    target_user = await db.get(User, user_id)
    if (not target_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' does not exist."
        )

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(target_user, field, value)

    await db.commit()
    await db.refresh(target_user)
    return target_user

# POST Routers

router.add_api_route(
    "",
    register_new_user,
    methods=["POST"],
    response_model=User_Read,
    status_code=status.HTTP_201_CREATED,
)

# DELETE Routers

@router.delete("/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    target_user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("users:delete"))
):
    target_user = await db.get(User, target_user_id)
    if (not target_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{target_user_id}' does not exist."
        )

    await db.delete(target_user)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)