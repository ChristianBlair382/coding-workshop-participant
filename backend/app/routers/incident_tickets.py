from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db, require_permission
from app.orm_models import (
    Engineer,
    Incident_Ticket,
    USER_ROLE,
    User,
)
from app.orm_models.enums import ENGINEER_STATUS, INCIDENT_TICKET_STATUS
from app.schemas import (
    Incident_Ticket_Create,
    Incident_Ticket_Read,
    Incident_Ticket_Update,
)

router = APIRouter(prefix="/incident-tickets", tags=["incident-tickets"])


def _accessible_tickets(user: User):
    query = select(Incident_Ticket).options(
        selectinload(Incident_Ticket.creator),
    )
    if user.role == USER_ROLE.EMP:
        return query.where(Incident_Ticket.created_by_id == user.id)
    if user.role == USER_ROLE.ENG:
        return query.where(
            or_(
                Incident_Ticket.created_by_id == user.id,
                Incident_Ticket.assigned_engineer.has(
                    Engineer.user_id == user.id
                ),
            )
        )
    return query


@router.get("", response_model=list[Incident_Ticket_Read])
async def list_incident_tickets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("incident_tickets:read")),
) -> list[Incident_Ticket]:
    """List all incident tickets."""
    result = await db.scalars(
        _accessible_tickets(current_user).order_by(Incident_Ticket.id)
    )
    return list(result.all())


@router.get("/{ticket_id}", response_model=Incident_Ticket_Read)
async def get_incident_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("incident_tickets:read")),
) -> Incident_Ticket:
    """Get an incident ticket by ID."""
    result = await db.scalars(
        _accessible_tickets(current_user).where(Incident_Ticket.id == ticket_id)
    )
    ticket = result.one_or_none()
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident ticket not found.")
    return ticket


@router.post(
    "",
    response_model=Incident_Ticket_Read,
    status_code=status.HTTP_201_CREATED,
)
async def create_incident_ticket(
    payload: Incident_Ticket_Create,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("incident_tickets:create")),
) -> Incident_Ticket:
    """Create an incident ticket."""
    ticket_data = payload.model_dump()
    ticket_data["created_by_id"] = current_user.id
    if current_user.role == USER_ROLE.ENG:
        assigned_engineer = await db.scalar(
            select(Engineer).where(Engineer.user_id == current_user.id)
        )
        if assigned_engineer is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Your engineer profile is not available for ticket assignment.",
            )
        ticket_data["assigned_engineer_id"] = assigned_engineer.id
    elif current_user.role == USER_ROLE.EMP or ticket_data["assigned_engineer_id"] is None:
        if current_user.role == USER_ROLE.EMP:
            assigned_engineer = await db.scalar(
                select(Engineer)
                .where(Engineer.status == ENGINEER_STATUS.AVAILABLE)
                .order_by(Engineer.id)
            )
            if assigned_engineer is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No available engineer can be assigned to this ticket.",
                )
            ticket_data["assigned_engineer_id"] = assigned_engineer.id
    now = func.now()
    if ticket_data["status"] != INCIDENT_TICKET_STATUS.OPEN:
        ticket_data["acknowledged_at"] = now
    if ticket_data["assigned_engineer_id"] is not None:
        ticket_data["assigned_at"] = now
    if ticket_data["status"] in {
        INCIDENT_TICKET_STATUS.RESOLVED,
        INCIDENT_TICKET_STATUS.CLOSED,
    }:
        ticket_data["completed_at"] = now
    ticket = Incident_Ticket(**ticket_data)
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    await db.refresh(ticket, attribute_names=["creator"])
    return ticket


@router.patch("/{ticket_id}", response_model=Incident_Ticket_Read)
async def update_incident_ticket(
    ticket_id: int,
    payload: Incident_Ticket_Update,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("incident_tickets:update")),
) -> Incident_Ticket:
    """Update an incident ticket."""
    result = await db.scalars(
        _accessible_tickets(current_user).where(Incident_Ticket.id == ticket_id)
    )
    ticket = result.one_or_none()
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident ticket not found.")
    changes = payload.model_dump(exclude_unset=True)
    if current_user.role == USER_ROLE.ENG:
        engineer = await db.scalar(
            select(Engineer).where(Engineer.user_id == current_user.id)
        )
        if engineer is None or ticket.assigned_engineer_id != engineer.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident ticket not found.")
        if not changes.keys() <= {"status", "priority"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Engineers may only update ticket status and priority.",
            )
    previous_status = ticket.status
    previous_assigned_engineer_id = ticket.assigned_engineer_id
    for field, value in changes.items():
        setattr(ticket, field, value)
    if (
        previous_status == INCIDENT_TICKET_STATUS.OPEN
        and ticket.status != INCIDENT_TICKET_STATUS.OPEN
        and ticket.acknowledged_at is None
    ):
        ticket.acknowledged_at = func.now()
    if (
        previous_assigned_engineer_id is None
        and ticket.assigned_engineer_id is not None
        and ticket.assigned_at is None
    ):
        ticket.assigned_at = func.now()
    completed_statuses = {
        INCIDENT_TICKET_STATUS.RESOLVED,
        INCIDENT_TICKET_STATUS.CLOSED,
    }
    if (
        previous_status not in completed_statuses
        and ticket.status in completed_statuses
        and ticket.completed_at is None
    ):
        ticket.completed_at = func.now()
    await db.commit()
    await db.refresh(ticket)
    await db.refresh(ticket, attribute_names=["creator"])
    return ticket


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_incident_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("incident_tickets:delete")),
) -> Response:
    """Delete an incident ticket."""
    ticket = await db.get(Incident_Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident ticket not found.")
    await db.delete(ticket)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
