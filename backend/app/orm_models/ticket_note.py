from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .incident_ticket import Incident_Ticket
    from .user import User

class Ticket_Note(Base):
    """User-authored message attached to an incident ticket."""

    __tablename__ = "ticket_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    incident_ticket_id: Mapped[int] = mapped_column(
        ForeignKey("incident_tickets.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    incident_ticket: Mapped["Incident_Ticket"] = relationship(back_populates="ticket_notes")
    author: Mapped["User"] = relationship(back_populates="authored_ticket_notes")
    attachments: Mapped[list["Ticket_Note_Attachment"]] = relationship(
        back_populates="ticket_note",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"Ticket Note (ID = {self.id}, Incident Ticket ID = "
            f"{self.incident_ticket_id}, Author ID = {self.author_id}, "
            f"Created At = {self.created_at})"
        )


class Ticket_Note_Attachment(Base):
    """Uploaded file reference associated with a ticket note."""

    __tablename__ = "ticket_note_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    ticket_note_id: Mapped[int] = mapped_column(
        ForeignKey("ticket_notes.id", ondelete="CASCADE"),
        nullable=False,
    )

    ticket_note: Mapped["Ticket_Note"] = relationship(back_populates="attachments")

    def __repr__(self) -> str:
        return (
            f"Ticket Note Attachment (ID = {self.id}, "
            f"Ticket Note ID = {self.ticket_note_id}, File URL = {self.file_url!r})"
        )