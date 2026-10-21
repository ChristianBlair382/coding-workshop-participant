from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db, require_permission
from app.orm_models import (
    Engineer,
    Incident_Ticket,
    Ticket_Note,
    Ticket_Note_Attachment,
    USER_ROLE,
    User,
)
from app.schemas import Ticket_Note_Create, Ticket_Note_Read, Ticket_Note_Update

router = APIRouter(prefix="/ticket-notes", tags=["ticket-notes"])


def _visible_notes_query(current_user: User):
    query = select(Ticket_Note)
    if current_user.role == USER_ROLE.FA:
        return query

    query = query.join(Ticket_Note.incident_ticket).outerjoin(
        Incident_Ticket.assigned_engineer
    )
    if current_user.role == USER_ROLE.EMP:
        query = query.where(Incident_Ticket.created_by_id == current_user.id)
    else:
        query = query.where(
            or_(
                Incident_Ticket.created_by_id == current_user.id,
                Engineer.user_id == current_user.id,
            )
        )
    return query.where(
        or_(
            Ticket_Note.author_id == Incident_Ticket.created_by_id,
            Ticket_Note.author_id == Engineer.user_id,
        )
    )


@router.get("", response_model=list[Ticket_Note_Read])
async def list_ticket_notes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("ticket_notes:read")),
) -> list[Ticket_Note]:
    """List ticket notes with their attachments."""
    result = await db.scalars(
        _visible_notes_query(current_user)
        .options(
            selectinload(Ticket_Note.attachments),
            selectinload(Ticket_Note.author),
        )
        .order_by(Ticket_Note.id)
    )
    return list(result.all())


@router.get("/{note_id}", response_model=Ticket_Note_Read)
async def get_ticket_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("ticket_notes:read")),
) -> Ticket_Note:
    """Get a ticket note with its attachments."""
    result = await db.scalars(
        _visible_notes_query(current_user)
        .options(
            selectinload(Ticket_Note.attachments),
            selectinload(Ticket_Note.author),
        )
        .where(Ticket_Note.id == note_id)
    )
    note = result.one_or_none()
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket note not found.")
    return note


@router.post("", response_model=Ticket_Note_Read, status_code=status.HTTP_201_CREATED)
async def create_ticket_note(
    payload: Ticket_Note_Create,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("ticket_notes:create")),
) -> Ticket_Note:
    """Create a ticket note and any included attachments."""
    note_data = payload.model_dump(exclude={"attachments"})
    ticket_query = select(Incident_Ticket).where(
        Incident_Ticket.id == payload.incident_ticket_id
    )
    if current_user.role == USER_ROLE.EMP:
        ticket_query = ticket_query.where(
            Incident_Ticket.created_by_id == current_user.id
        )
    elif current_user.role == USER_ROLE.ENG:
        ticket_query = ticket_query.where(
            or_(
                Incident_Ticket.created_by_id == current_user.id,
                Incident_Ticket.assigned_engineer.has(
                    Engineer.user_id == current_user.id
                ),
            )
        )
    ticket = await db.scalar(ticket_query)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident ticket not found.",
        )
    note_data["author_id"] = current_user.id
    note = Ticket_Note(
        **note_data,
        attachments=[
            Ticket_Note_Attachment(**attachment.model_dump())
            for attachment in payload.attachments
        ],
    )
    db.add(note)
    await db.commit()
    result = await db.scalars(
        select(Ticket_Note)
        .options(
            selectinload(Ticket_Note.attachments),
            selectinload(Ticket_Note.author),
        )
        .where(Ticket_Note.id == note.id)
    )
    created_note = result.one()
    return created_note


@router.patch("/{note_id}", response_model=Ticket_Note_Read)
async def update_ticket_note(
    note_id: int,
    payload: Ticket_Note_Update,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("ticket_notes:update")),
) -> Ticket_Note:
    """Update a ticket note."""
    note = await db.get(Ticket_Note, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket note not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    await db.commit()
    result = await db.scalars(
        select(Ticket_Note)
        .options(
            selectinload(Ticket_Note.attachments),
            selectinload(Ticket_Note.author),
        )
        .where(Ticket_Note.id == note_id)
    )
    updated_note = result.one()
    return updated_note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("ticket_notes:delete")),
) -> Response:
    """Delete a ticket note and its attachments."""
    note = await db.get(Ticket_Note, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket note not found.")
    await db.delete(note)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
