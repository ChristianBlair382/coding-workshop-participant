from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_permission
from app.orm_models import User, Refresh_Token
from app.schemas import User_Create, User_Read, Token, Refresh_Token_Request
from app.security import create_access_token, encrypt_password, verify_password, create_refresh_token, hash_refresh_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/token", response_model=Token)
async def login(
    login_form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Token:
    db_command = select(User).where(User.username == login_form_data.username)
    output = await db.execute(db_command)
    target_user = output.scalar_one_or_none()

    # Checks that the username of the specified User is correct, along with their password.
    if (target_user is None or not verify_password(login_form_data.password, target_user.hashed_password)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username or Password is incorrect.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    new_access_token = create_access_token(data={"sub": target_user.username, "role": target_user.role.value})

    created_at = datetime.now(timezone.utc)
    raw_refresh_token = create_refresh_token()

    new_refresh_token = Refresh_Token(
        user_id = target_user.id,
        token_hash = hash_refresh_token(raw_refresh_token),
        created_at = created_at,
        expires_at = created_at + timedelta(days=Refresh_Token.DAYS_TILL_EXPIRE),
    )
    db.add(new_refresh_token)
    await db.commit()
    return Token(access_token=new_access_token, refresh_token=raw_refresh_token, token_type="bearer")

@router.post("/register", response_model=User_Read, status_code=status.HTTP_201_CREATED)
async def register_new_user(
    payload: User_Create,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("users:create"))
) -> User:
    # Check that there isn't a User in the database with the same username as the attempted payload.
    db_command = select(User).where(func.lower(User.username) == payload.username.lower())
    existing_user = await db.execute(db_command)
    if (existing_user.scalar_one_or_none() is not None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{payload.username}' already exists. Please try a different username.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # If no such User exists, proceed with creating a new user.
    new_user = User(
        username = payload.username,
        email = payload.email,
        hashed_password = encrypt_password(payload.password),
        role = payload.role
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    payload: Refresh_Token_Request,
    db: AsyncSession = Depends(get_db),
) -> Token:
    # Once an access token for a user's session expires, call this route to replace their deprecated 
    # access token with a new one. Also, replace refresh token.

    # Stamp the current time for later use.
    now = datetime.now(timezone.utc)

    # Find the refresh token by it's hashed version.
    hashed_refresh_token = hash_refresh_token(payload.refresh_token)
    db_command = (
        select(Refresh_Token)
        .where(Refresh_Token.token_hash == hashed_refresh_token)
        .with_for_update()
    )
    refresh_token_output = await db.execute(db_command)
    target_refresh_token = refresh_token_output.scalar_one_or_none()

    # Verify that the refresh token exists...
    if target_refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token. [DOES NOT EXIST]",
        )

    # ...has not already been revoked...
    # (If it has, revoke all refresh tokens with the same family_id immediately)
    if target_refresh_token.revoked_at is not None:
        family_query_command = (
            select(Refresh_Token)
            .where(
                Refresh_Token.family_id == target_refresh_token.family_id, 
                Refresh_Token.revoked_at.is_(None)
            )
            .with_for_update()
        )
        family_output = await db.execute(family_query_command)

        for active_token in family_output.scalars():
            active_token.revoked_at = now

        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token. [FAMILY_ID REVOKED]",
        )

    # ...and has not expired.
    if now >= target_refresh_token.expires_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token. [EXPIRED]",
        )

    # Find and verify that the user associated with this token exists and is active.
    target_user = await db.get(User, target_refresh_token.user_id)
    if (
        target_user is None or 
        not target_user.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token. [USER TABLE QUERY ERROR]",
        )

    # Add a revocation date to the now deprecated refresh token.
    target_refresh_token.revoked_at = datetime.now(timezone.utc)

    # Create a new access token and refresh token. When making a new refresh token this way, use the family_id used by the previous token.
    new_access_token = create_access_token(data={"sub": target_user.username, "role": target_user.role.value})
    new_raw_refresh_token = create_refresh_token()
    new_refresh_token = Refresh_Token(
        user_id = target_user.id,
        family_id = target_refresh_token.family_id,
        token_hash = hash_refresh_token(new_raw_refresh_token),
        created_at = now,
        expires_at = now + timedelta(days=Refresh_Token.DAYS_TILL_EXPIRE),
    )

    # Add the new refresh token
    db.add(new_refresh_token)
    await db.commit()
    return Token(access_token=new_access_token, refresh_token=new_raw_refresh_token, token_type="bearer")