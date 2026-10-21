from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_permission
from app.orm_models import (
    Engineer,
    Incident_Ticket,
    Ticket_Note,
    Ticket_Note_Attachment,
    USER_ROLE,
    User,
)
from app.schemas import (
    Ticket_Note_Attachment_Create,
    Ticket_Note_Attachment_Read,
    Ticket_Note_Attachment_Update,
)

router = APIRouter(
    prefix="/ticket-note-attachments",
    tags=["ticket-note-attachments"],
)


@router.get("", response_model=list[Ticket_Note_Attachment_Read])
async def list_ticket_note_attachments(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("ticket_note_attachments:read")),
) -> list[Ticket_Note_Attachment]:
    """List all ticket note attachments."""
    result = await db.scalars(
        select(Ticket_Note_Attachment).order_by(Ticket_Note_Attachment.id)
    )
    return list(result.all())


@router.get("/{attachment_id}", response_model=Ticket_Note_Attachment_Read)
async def get_ticket_note_attachment(
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("ticket_note_attachments:read")),
) -> Ticket_Note_Attachment:
    """Get a ticket note attachment by ID."""
    attachment = await db.get(Ticket_Note_Attachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket note attachment not found.")
    return attachment


@router.post(
    "",
    response_model=Ticket_Note_Attachment_Read,
    status_code=status.HTTP_201_CREATED,
)
async def create_ticket_note_attachment(
    payload: Ticket_Note_Attachment_Create,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("ticket_note_attachments:create")),
) -> Ticket_Note_Attachment:
    """Create a ticket note attachment."""
    note_query = (
        select(Ticket_Note)
        .join(Ticket_Note.incident_ticket)
        .where(Ticket_Note.id == payload.ticket_note_id)
    )
    if current_user.role == USER_ROLE.EMP:
        note_query = note_query.where(
            Incident_Ticket.created_by_id == current_user.id,
            Ticket_Note.author_id == current_user.id,
        )
    elif current_user.role == USER_ROLE.ENG:
        note_query = note_query.join(Incident_Ticket.assigned_engineer).where(
            or_(
                Incident_Ticket.created_by_id == current_user.id,
                Engineer.user_id == current_user.id,
            ),
            Ticket_Note.author_id == current_user.id,
        )
    note = await db.scalar(note_query)
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket note not found.",
        )
    attachment = Ticket_Note_Attachment(**payload.model_dump())
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)
    return attachment


@router.patch(
    "/{attachment_id}",
    response_model=Ticket_Note_Attachment_Read,
)
async def update_ticket_note_attachment(
    attachment_id: int,
    payload: Ticket_Note_Attachment_Update,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("ticket_note_attachments:update")),
) -> Ticket_Note_Attachment:
    """Update a ticket note attachment."""
    attachment = await db.get(Ticket_Note_Attachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket note attachment not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(attachment, field, value)
    await db.commit()
    await db.refresh(attachment)
    return attachment


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket_note_attachment(
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("ticket_note_attachments:delete")),
) -> Response:
    """Delete a ticket note attachment."""
    attachment = await db.get(Ticket_Note_Attachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket note attachment not found.")
    await db.delete(attachment)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
