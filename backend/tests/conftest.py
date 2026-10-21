import os
import pytest_asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.dependencies import get_db
from app.main import app
from app.orm_models import (
    Base, 
    Building, 
    Floor,
    Seat,
    Engineer, 
    ENGINEER_FIELD,
    ENGINEER_STATUS,
    Incident_Ticket, 
    INCIDENT_TICKET_STATUS, 
    INCIDENT_TICKET_PRIORITY, 
    Ticket_Note, 
    Ticket_Note_Attachment, 
    User,
    USER_ROLE
)
from app.security import create_access_token, encrypt_password

TEST_DB_URL = os.environ.get(
    "TEST_DB_URL",
    "postgresql+asyncpg://postgres:L%40ctoseFr33@localhost:5432/citibank_test"
)

test_engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)

@pytest_asyncio.fixture
async def db_session():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def seeded_users(db_session):
    users = {
        "admin": User(
            username="test_admin", 
            hashed_password=encrypt_password("pw"), 
            role=USER_ROLE.FOA
        ),
        "field_hand": User(
            username="test_field_hand", 
            hashed_password=encrypt_password("pw"), 
            role=USER_ROLE.FH
        ),
        "auditor": User(
            username="test_auditor", 
            hashed_password=encrypt_password("pw"), 
            role=USER_ROLE.AUD
        )
    }

    for user in users.values():
        db_session.add(user)
    await db_session.commit()
    for user in users.values():
        db_session.refresh(user)
    return users

@pytest_asyncio.fixture
async def seeded_supervisor(db_session):
    supervisor = Supervisor(name="test_name")
    db_session.add(supervisor)
    await db_session.commit()
    await db_session.refresh(supervisor)
    return supervisor

@pytest_asyncio.fixture
async def seeded_farm(db_session, seeded_supervisor):
    farm = Farm(
        name="test_farm", 
        location_region="test_region", 
        capacity=12, 
        supervisor_id=seeded_supervisor.id
    )
    db_session.add(farm)
    await db_session.commit()
    await db_session.refresh(farm)
    return farm

@pytest_asyncio.fixture
async def seeded_hand(db_session, seeded_farm):
    hand = Hand(name="test_hand", farm_id=seeded_farm.id)
    db_session.add(hand)
    await db_session.commit()
    await db_session.refresh(hand)
    return hand

@pytest_asyncio.fixture
async def seeded_equipment(db_session, seeded_farm):
    equipment = Equipment(
        serial_num="test_serial", 
        model="test_model", 
        fuel_lvl=45.66, 
        farm_id=seeded_farm.id, 
        status=EQUIPMENT_STATUS.IDLE
    )
    db_session.add(equipment)
    await db_session.commit()
    await db_session.refresh(equipment)
    return equipment

@pytest_asyncio.fixture
async def seeded_field_job(db_session, seeded_equipment, seeded_hand):
    field_job = Field_Job(
        title="test_title",
        equipment_id=seeded_equipment.id,
        hand_id=seeded_hand.id,
        priority=FIELD_JOB_PRIORITY.MEDIUM,
        status=FIELD_JOB_STATUS.PENDING
    )
    db_session.add(field_job)
    await db_session.commit()
    await db_session.refresh(field_job)
    return field_job

@pytest_asyncio.fixture
async def seeded_service_report(db_session, seeded_field_job):
    service_report = Service_Report(
        file_url="test_url",
        field_job_id=seeded_field_job.id,
        notes="test_notes"
    )
    db_session.add(service_report)
    await db_session.commit()
    await db_session.refresh(service_report)
    return service_report

def auth_header(user: User) -> dict[str, str]:
    token = create_access_token(data={"sub": user.username, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}