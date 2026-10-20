import jwt

from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status 
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.orm_models import Permission, RolePermission, User, USER_ROLE
from app.security import decode_access_token

from .database import AsyncSessionLocal

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    return user

def require_role(*allowed_roles: USER_ROLE) -> None:
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(f"Role '{current_user.role.value}' is not permitted to perform this action.")
            )
        return current_user
    return role_checker

def require_permission(*allowed_permissions: str) -> None:
    async def permission_checker(
            current_user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db),
    ) -> User:
        result = await db.execute(
            select(Permission.id)
            .join(RolePermission)
            .where(
                RolePermission.role == current_user.role.value,
                Permission.name.in_(allowed_permissions),
            )
            .limit(1)
        )

        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have '{allowed_permissions}' permission to perform this action.",
            )
        return current_user

    return permission_checker