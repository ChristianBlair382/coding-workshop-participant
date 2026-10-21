from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, Enum as SqlEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import INCIDENT_TICKET_STATUS, INCIDENT_TICKET_PRIORITY

if TYPE_CHECKING:
    from .engineer import Engineer
    from .ticket_note import Ticket_Note
    from .user import User

class Incident_Ticket(Base):
    """Incident submitted by a user and assigned to an engineer."""

    __tablename__ = "incident_tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=True,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[INCIDENT_TICKET_PRIORITY] = mapped_column(
        SqlEnum(
            INCIDENT_TICKET_PRIORITY,
            name="incident_ticket_priority",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=INCIDENT_TICKET_PRIORITY.MEDIUM,
    )
    status: Mapped[INCIDENT_TICKET_STATUS] = mapped_column(
        SqlEnum(
            INCIDENT_TICKET_STATUS,
            name="incident_ticket_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls]
        ),
        default=INCIDENT_TICKET_STATUS.OPEN,
    )
    assigned_engineer_id: Mapped[int] = mapped_column(
        ForeignKey("engineers.id"),
        nullable=True,
    )
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    assigned_engineer: Mapped["Engineer | None"] = relationship(
        back_populates="incident_tickets",
    )
    creator: Mapped["User"] = relationship(
        back_populates="created_incident_tickets",
        foreign_keys=[created_by_id],
    )
    ticket_notes: Mapped[list["Ticket_Note"]] = relationship(
        back_populates="incident_ticket",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"Incident Ticket (ID = {self.id}, Title = {self.title!r}, "
            f"Priority = {self.priority.value}, Status = {self.status.value}, "
            f"Assigned Engineer ID = {self.assigned_engineer_id}, "
            f"Creator ID = {self.created_by_id})"
        )
    
    def update_status(self, new_status: INCIDENT_TICKET_STATUS) -> None:
        """Update the ticket status after validating its enum value."""
        if not isinstance(new_status, INCIDENT_TICKET_STATUS):
            raise TypeError(f"Expected IncidentTicketStatus enum, got {type(new_status).__name__}")
        if self.status == new_status:
            return
        self.status = new_status

    def update_priority(self, new_priority: INCIDENT_TICKET_PRIORITY) -> None:
        """Update the ticket priority after validating its enum value."""
        if not isinstance(new_priority, INCIDENT_TICKET_PRIORITY):
            raise TypeError(f"Expected IncidentTicketPriority enum, got {type(new_priority).__name__}")
        if self.priority == new_priority:
            return
        self.priority = new_priority