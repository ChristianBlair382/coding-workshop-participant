from fastapi import APIRouter, HTTPException, status, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, require_permission
from app.orm_models import Permission, RolePermission, User, USER_ROLE
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