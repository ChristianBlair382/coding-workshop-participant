# Run with: python -m services.seed_tables
# From: backend/ with venv active

import asyncio
import sys
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.orm_models import (
    USER_ROLE,
    User,
    Permission,
    RolePermission,
)
from app.security import encrypt_password

PERMISSION_RESOURCES = (
    "farms",
    "equipments",
    "field_jobs",
    "service_reports",
    "hands",
    "supervisors",
    "users",
)
PERMISSION_ACTIONS = ("create", "read", "update", "delete")
ROLE_PERMISSIONS = {
    USER_ROLE.AUD: {
        f"{resource}:read"
        for resource in (
            "farms",
            "equipments",
            "field_jobs",
            "service_reports",
            "hands",
            "supervisors",
        )
    },
    USER_ROLE.FH: {
        f"{resource}:read"
        for resource in (
            "farms",
            "equipments",
            "field_jobs",
            "service_reports",
            "hands",
            "supervisors",
        )
    } | {
        "equipments:update",
        "field_jobs:update",
        "service_reports:create",
    },
    USER_ROLE.FOA: {
        f"{resource}:{action}"
        for resource in PERMISSION_RESOURCES
        for action in PERMISSION_ACTIONS
    },
}

async def seed_permissions(session: AsyncSession) -> None:
    permissions = {
        permission.name: permission
        for permission in (await session.scalars(select(Permission))).all()
    }
    new_permissions = {
        name: Permission(
            name=name,
            description=f"{action.title()} {resource.replace('_', ' ')}",
        )
        for resource in PERMISSION_RESOURCES
        for action in PERMISSION_ACTIONS
        for name in (f"{resource}:{action}",)
        if name not in permissions
    }
    permissions.update(new_permissions)
    session.add_all(new_permissions.values())
    await session.flush()

    assigned = set(
        (
            await session.execute(
                select(RolePermission.role, Permission.name)
                .join(Permission)
            )
        ).all()
    )
    new_assignments = []
    for role, permission_names in ROLE_PERMISSIONS.items():
        for name in permission_names:
            assignment = (role.value, name)
            if assignment not in assigned:
                new_assignments.append(
                    RolePermission(
                        role=role.value,
                        permission_id=permissions[name].id,
                    )
                )

    session.add_all(new_assignments)

async def seed_tables() -> None:
    async with AsyncSessionLocal() as session:
        await seed_permissions(session)

        session.add_all([
            User(
                username="facility_admin@acme.inc", 
                email="facility_admin123@acme.inc", 
                hashed_password=encrypt_password("FacilityAdmin123!"), 
                role=USER_ROLE.FA
            ),
            User(
                username="field_hand",
                email="engineer123@acme.inc",
                hashed_password=encrypt_password("Engineer123!"), 
                role=USER_ROLE.ENG
            ),
            User(
                username="auditor", 
                email="employee123@acme.inc",
                hashed_password=encrypt_password("Auditor123!"), 
                role=USER_ROLE.AUD
            ),
        ])
        await session.commit()

if __name__ == "__main__":
    try:
        asyncio.run(seed_tables())
    except IntegrityError:
        print(
            "Seeding failed: the database rejected a constant, possibly because "
            "seed data already exists or conflicts with existing records.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None