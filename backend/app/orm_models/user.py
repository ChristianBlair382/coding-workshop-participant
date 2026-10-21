from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import USER_ROLE

if TYPE_CHECKING:
    from .engineer import Engineer
    from .incident_ticket import Incident_Ticket
    from .seat import Seat
    from .ticket_note import Ticket_Note

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[USER_ROLE] = mapped_column(
        SqlEnum(
            USER_ROLE,
            name="user_role",
            values_callable= lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=USER_ROLE.EMP,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    engineer: Mapped["Engineer | None"] = relationship(back_populates="user")
    seats: Mapped[list["Seat"]] = relationship(back_populates="occupant")
    created_incident_tickets: Mapped[list["Incident_Ticket"]] = relationship(
        back_populates="creator",
        foreign_keys="Incident_Ticket.created_by_id",
    )
    authored_ticket_notes: Mapped[list["Ticket_Note"]] = relationship(
        back_populates="author",
    )

    def __repr__(self):
        return (f"User (ID = {self.id}, Username = {self.username!r}, Role = {self.role.value})")