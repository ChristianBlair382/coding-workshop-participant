# Run with: python -m services.seed_tables
# From: backend/ with venv active

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.orm_models import (
    ENGINEER_FIELD,
    ENGINEER_STATUS,
    INCIDENT_TICKET_PRIORITY,
    INCIDENT_TICKET_STATUS,
    USER_ROLE,
    Building,
    Engineer,
    Floor,
    Incident_Ticket,
    Seat,
    User,
    Permission,
    RolePermission,
    Ticket_Note,
)
from app.security import encrypt_password

PERMISSION_RESOURCES = (
    "users",
    "buildings",
    "engineers",
    "floors",
    "incident_tickets",
    "seats",
    "ticket_notes",
    "ticket_note_attachments",
)
PERMISSION_ACTIONS = ("create", "read", "update", "delete")
ROLE_PERMISSIONS = {
    USER_ROLE.EMP: {
        "incident_tickets:read",
        "incident_tickets:create",
        "ticket_notes:read",
        "ticket_notes:create",
        "ticket_note_attachments:create",
    },
    USER_ROLE.ENG: {
        "engineers:read",
        "incident_tickets:read",
        "incident_tickets:create",
        "incident_tickets:update",
        "ticket_notes:read",
        "ticket_notes:create",
        "ticket_note_attachments:create",
    },
    USER_ROLE.FA: {
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

    managed_permission_names = {
        f"{resource}:{action}"
        for resource in PERMISSION_RESOURCES
        for action in PERMISSION_ACTIONS
    }
    assigned_rows = (
        await session.execute(
            select(RolePermission, Permission.name)
            .join(Permission)
            .where(
                RolePermission.role.in_([role.value for role in ROLE_PERMISSIONS])
            )
        )
    ).all()
    assigned = {
        (assignment.role, permission_name)
        for assignment, permission_name in assigned_rows
    }
    desired_assignments = {
        (role.value, name)
        for role, names in ROLE_PERMISSIONS.items()
        for name in names
    }
    stale_assignments = [
        assignment
        for assignment, permission_name in assigned_rows
        if permission_name in managed_permission_names
        and (assignment.role, permission_name) not in desired_assignments
    ]
    for assignment in stale_assignments:
        await session.delete(assignment)

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


async def seed_office_and_occupants(
    session: AsyncSession,
    admin: User,
    engineer_users: dict[str, User],
) -> list[User]:
    """Seed one three-floor building with a distinct user in each of 60 seats."""
    employee = await session.scalar(
        select(User).where(User.username == "employee")
    )
    if employee is None or employee.role != USER_ROLE.EMP:
        raise RuntimeError("The employee seed user must exist with the Employee role.")

    dummy_employee_specs = [
        (f"office_employee_{number:02}", f"office_employee_{number:02}@acme.inc")
        for number in range(1, 54)
    ]
    dummy_usernames = [username for username, _ in dummy_employee_specs]
    dummy_emails = [email for _, email in dummy_employee_specs]
    existing_dummy_users = (
        await session.scalars(
            select(User).where(
                or_(
                    User.username.in_(dummy_usernames),
                    User.email.in_(dummy_emails),
                )
            )
        )
    ).all()
    users_by_username = {user.username: user for user in existing_dummy_users}
    users_by_email = {user.email: user for user in existing_dummy_users}

    dummy_employees: list[User] = []
    new_dummy_employees: list[User] = []
    for username, email in dummy_employee_specs:
        existing_by_username = users_by_username.get(username)
        existing_by_email = users_by_email.get(email)
        if existing_by_username is not None or existing_by_email is not None:
            if existing_by_username is None or existing_by_username is not existing_by_email:
                raise RuntimeError(
                    f"Seed employee account '{username}' conflicts with an existing username or email."
                )
            if existing_by_username.role != USER_ROLE.EMP:
                raise RuntimeError(
                    f"Seed employee account '{username}' must have the Employee role."
                )
            dummy_employees.append(existing_by_username)
            continue

        user = User(
            username=username,
            email=email,
            hashed_password=encrypt_password("Employee123!"),
            role=USER_ROLE.EMP,
        )
        dummy_employees.append(user)
        new_dummy_employees.append(user)

    session.add_all(new_dummy_employees)
    await session.flush()

    office_users = [
        admin,
        *(engineer_users[username] for username in (
            "field_hand",
            "engineer_02",
            "engineer_03",
            "engineer_04",
            "engineer_05",
        )),
        employee,
        *dummy_employees,
    ]
    if len(office_users) != 60 or len({user.id for user in office_users}) != 60:
        raise RuntimeError("The seeded office must have exactly 60 distinct occupant users.")
    if sum(user.role == USER_ROLE.FA for user in office_users) != 1:
        raise RuntimeError("The seeded office must have exactly one Facility Admin occupant.")

    building_name = "[Seed] ACME Headquarters"
    buildings = (
        await session.scalars(
            select(Building).where(Building.name == building_name)
        )
    ).all()
    if len(buildings) > 1:
        raise RuntimeError(f"More than one seed building named '{building_name}' exists.")
    building = buildings[0] if buildings else Building(
        name=building_name,
        location="New York",
        floor_count=3,
    )
    building.location = "New York"
    building.floor_count = 3
    if not buildings:
        session.add(building)
    await session.flush()

    floor_specs = [("1", 20), ("2", 20), ("3", 20)]
    existing_floors = (
        await session.scalars(
            select(Floor).where(Floor.building_id == building.id)
        )
    ).all()
    floors_by_name = {floor.floor_id: floor for floor in existing_floors}
    if len(floors_by_name) != len(existing_floors):
        raise RuntimeError("The seed building has duplicate floor identifiers.")

    floors: list[Floor] = []
    new_floors: list[Floor] = []
    for floor_name, seat_count in floor_specs:
        floor = floors_by_name.get(floor_name)
        if floor is None:
            floor = Floor(
                floor_id=floor_name,
                seat_count=seat_count,
                building=building,
            )
            new_floors.append(floor)
        else:
            floor.seat_count = seat_count
        floors.append(floor)
    session.add_all(new_floors)
    await session.flush()

    existing_seats = (
        await session.scalars(
            select(Seat).where(Seat.floor_id.in_([floor.id for floor in floors]))
        )
    ).all()
    seats_by_key = {
        (seat.floor_id, seat.seat_id): seat for seat in existing_seats
    }
    if len(seats_by_key) != len(existing_seats):
        raise RuntimeError("The seed floors contain duplicate seat identifiers.")

    new_seats: list[Seat] = []
    occupant_index = 0
    for floor in floors:
        for seat_number in range(1, 21):
            seat_name = f"F{floor.floor_id}-{seat_number:02}"
            seat = seats_by_key.get((floor.id, seat_name))
            occupant = office_users[occupant_index]
            occupant_index += 1
            if seat is None:
                seat = Seat(
                    seat_id=seat_name,
                    floor=floor,
                    occupant=occupant,
                )
                new_seats.append(seat)
            else:
                seat.occupant = occupant

    session.add_all(new_seats)
    await session.flush()
    return office_users


async def seed_incident_workflow(session: AsyncSession) -> None:
    """Seed engineer accounts, incident tickets, and three notes per ticket."""
    admin = await session.scalar(
        select(User).where(User.username == "facility_admin")
    )
    if admin is None or admin.role != USER_ROLE.FA:
        raise RuntimeError("The facility_admin seed user must exist with the Facility Admin role.")

    engineer_specs = [
        ("field_hand", "engineer123@acme.inc", "Building Engineer 1", ENGINEER_FIELD.BUILDING),
        ("engineer_02", "engineer_02@acme.inc", "Hardware Engineer 2", ENGINEER_FIELD.HARDWARE),
        ("engineer_03", "engineer_03@acme.inc", "Software Engineer 3", ENGINEER_FIELD.SOFTWARE),
        ("engineer_04", "engineer_04@acme.inc", "Electrical Engineer 4", ENGINEER_FIELD.ELECTRICAL),
        ("engineer_05", "engineer_05@acme.inc", "Building Engineer 5", ENGINEER_FIELD.BUILDING),
    ]
    engineer_usernames = [username for username, _, _, _ in engineer_specs]
    engineer_emails = [email for _, email, _, _ in engineer_specs]
    matching_users = (
        await session.scalars(
            select(User).where(
                or_(
                    User.username.in_(engineer_usernames),
                    User.email.in_(engineer_emails),
                )
            )
        )
    ).all()
    users_by_username = {user.username: user for user in matching_users}
    users_by_email = {user.email: user for user in matching_users}

    engineer_users: dict[str, User] = {}
    new_users: list[User] = []
    for username, email, name, _ in engineer_specs:
        existing_by_username = users_by_username.get(username)
        existing_by_email = users_by_email.get(email)
        if existing_by_username is not None or existing_by_email is not None:
            if existing_by_username is None or existing_by_username is not existing_by_email:
                raise RuntimeError(
                    f"Seed engineer account '{username}' conflicts with an existing username or email."
                )
            if existing_by_username.role != USER_ROLE.ENG:
                raise RuntimeError(
                    f"Seed engineer account '{username}' must have the Engineer role."
                )
            engineer_users[username] = existing_by_username
            continue

        engineer_user = User(
            username=username,
            email=email,
            hashed_password=encrypt_password("Engineer123!"),
            role=USER_ROLE.ENG,
        )
        new_users.append(engineer_user)
        engineer_users[username] = engineer_user

    session.add_all(new_users)
    await session.flush()

    existing_engineers = (
        await session.scalars(
            select(Engineer).where(
                Engineer.user_id.in_(
                    [user.id for user in engineer_users.values()]
                )
            )
        )
    ).all()
    engineers_by_user_id = {
        engineer.user_id: engineer for engineer in existing_engineers
    }
    engineers: dict[str, Engineer] = {}
    new_engineers: list[Engineer] = []
    for username, _, name, field in engineer_specs:
        engineer_user = engineer_users[username]
        engineer = engineers_by_user_id.get(engineer_user.id)
        if engineer is None:
            engineer = Engineer(
                name=name,
                user_id=engineer_user.id,
                field=field,
                status=ENGINEER_STATUS.AVAILABLE,
            )
            new_engineers.append(engineer)
        engineers[username] = engineer

    session.add_all(new_engineers)
    await session.flush()

    office_users = await seed_office_and_occupants(
        session,
        admin,
        engineer_users,
    )

    ticket_specs = [
        (
            "[Seed] North Campus - HVAC noise",
            "A persistent rattling noise is coming from the north campus HVAC unit.",
            "field_hand",
            INCIDENT_TICKET_PRIORITY.MEDIUM,
            INCIDENT_TICKET_STATUS.IN_PROGRESS,
        ),
        (
            "[Seed] Finance floor - network outage",
            "Several workstations on the finance floor cannot reach internal services.",
            "engineer_02",
            INCIDENT_TICKET_PRIORITY.CRITICAL,
            INCIDENT_TICKET_STATUS.BLOCKED,
        ),
        (
            "[Seed] Mobile app - sign-in failure",
            "The mobile application rejects valid credentials after the latest release.",
            "engineer_03",
            INCIDENT_TICKET_PRIORITY.CRITICAL,
            INCIDENT_TICKET_STATUS.OPEN,
        ),
        (
            "[Seed] Data center - lighting fault",
            "The emergency lighting circuit in the data center is intermittent.",
            "engineer_04",
            INCIDENT_TICKET_PRIORITY.MEDIUM,
            INCIDENT_TICKET_STATUS.IN_PROGRESS,
        ),
        (
            "[Seed] South Campus - conference room power",
            "Power outlets in conference room 3B are not providing power.",
            "engineer_05",
            INCIDENT_TICKET_PRIORITY.LOW,
            INCIDENT_TICKET_STATUS.OPEN,
        ),
        (
            "[Seed] West office - printer queue",
            "The shared printer queue is stalled and jobs remain pending.",
            "engineer_02",
            INCIDENT_TICKET_PRIORITY.LOW,
            INCIDENT_TICKET_STATUS.RESOLVED,
        ),
        (
            "[Seed] Headquarters - access control",
            "The west entrance badge reader is intermittently offline.",
            "engineer_04",
            INCIDENT_TICKET_PRIORITY.CRITICAL,
            INCIDENT_TICKET_STATUS.IN_PROGRESS,
        ),
    ]
    ticket_titles = [title for title, *_ in ticket_specs]
    existing_tickets = (
        await session.scalars(
            select(Incident_Ticket).where(Incident_Ticket.title.in_(ticket_titles))
        )
    ).all()
    tickets_by_title = {ticket.title: ticket for ticket in existing_tickets}
    new_tickets: list[Incident_Ticket] = []
    seeded_at = datetime.now(timezone.utc)
    for ticket_index, (
        title,
        description,
        engineer_username,
        priority,
        ticket_status,
    ) in enumerate(ticket_specs):
        ticket = tickets_by_title.get(title)
        creator = office_users[ticket_index + 1]
        created_at = seeded_at - timedelta(days=21 - ticket_index)
        acknowledged_at = created_at + timedelta(minutes=20 + ticket_index * 25)
        assigned_at = acknowledged_at + timedelta(hours=1 + ticket_index)
        completed_at = assigned_at + timedelta(hours=4 + ticket_index * 3)
        if ticket is None:
            ticket = Incident_Ticket(
                title=title,
                description=description,
                priority=priority,
                status=ticket_status,
                assigned_engineer=engineers[engineer_username],
                creator=creator,
                created_at=created_at,
                acknowledged_at=acknowledged_at,
                assigned_at=assigned_at,
                completed_at=completed_at,
            )
            new_tickets.append(ticket)
        else:
            ticket.creator = creator
            ticket.created_at = created_at
            ticket.acknowledged_at = acknowledged_at
            ticket.assigned_at = assigned_at
            ticket.completed_at = completed_at
        tickets_by_title[title] = ticket

    session.add_all(new_tickets)
    await session.flush()

    note_specs: list[tuple[Incident_Ticket, User, str]] = []
    for title, _, engineer_username, _, _ in ticket_specs:
        ticket = tickets_by_title[title]
        engineer_user = engineer_users[engineer_username]
        note_specs.extend(
            [
                (
                    ticket,
                    engineer_user,
                    f"[Seed] {title}: I have started investigating and will share findings.",
                ),
                (
                    ticket,
                    admin,
                    f"[Seed] {title}: Thank you. Please let me know if you need more details.",
                ),
                (
                    ticket,
                    engineer_user,
                    f"[Seed] {title}: I have completed the next diagnostic step and updated the ticket.",
                ),
            ]
        )

    seeded_ticket_ids = [ticket.id for ticket in tickets_by_title.values()]
    existing_notes = (
        await session.scalars(
            select(Ticket_Note).where(
                Ticket_Note.incident_ticket_id.in_(seeded_ticket_ids)
            )
        )
    ).all()
    existing_note_keys = {
        (note.incident_ticket_id, note.notes) for note in existing_notes
    }
    session.add_all(
        Ticket_Note(
            incident_ticket=ticket,
            author=author,
            notes=text,
        )
        for ticket, author, text in note_specs
        if (ticket.id, text) not in existing_note_keys
    )


async def seed_tables() -> None:
    async with AsyncSessionLocal() as session:
        await seed_permissions(session)

        seed_users = [
            User(
                username="facility_admin", 
                email="facility_admin123@acme.inc", 
                hashed_password=encrypt_password("FacilityAdmin123!"), 
                role=USER_ROLE.FA
            ),
            User(
                username="engineer",
                email="engineer246@acme.inc",
                hashed_password=encrypt_password("Engineer246!"),
                role=USER_ROLE.ENG
            ),
            User(
                username="employee", 
                email="employee123@acme.inc",
                hashed_password=encrypt_password("Employee123!"), 
                role=USER_ROLE.EMP
            ),
        ]
        existing_users = (
            await session.execute(
                select(User.username, User.email).where(
                    or_(
                        User.username.in_([user.username for user in seed_users]),
                        User.email.in_([user.email for user in seed_users]),
                    )
                )
            )
        ).all()
        existing_usernames = {username for username, _ in existing_users}
        existing_emails = {email for _, email in existing_users}
        session.add_all(
            user
            for user in seed_users
            if user.username not in existing_usernames
            and user.email not in existing_emails
        )
        await session.flush()
        await seed_incident_workflow(session)
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