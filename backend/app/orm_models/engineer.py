from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import ENGINEER_STATUS, ENGINEER_FIELD

if TYPE_CHECKING:
    from .incident_ticket import Incident_Ticket
    from .user import User

class Engineer(Base):
    __tablename__ = "engineers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    field: Mapped[ENGINEER_FIELD] = mapped_column(
        SqlEnum(
            ENGINEER_FIELD,
            name="engineer_field",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=ENGINEER_FIELD.BUILDING,
    )
    status: Mapped[ENGINEER_STATUS] = mapped_column(
        SqlEnum(
            ENGINEER_STATUS,
            name="engineer_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=ENGINEER_STATUS.AVAILABLE,
    )

    user: Mapped["User"] = relationship(back_populates="engineer")
    incident_tickets: Mapped[list["Incident_Ticket"]] = relationship(
        back_populates="assigned_engineer",
    )

    def __repr__(self) -> str:
        return f"Engineer (ID = {self.id}, Name = {self.name}, User ID = {self.user_id})"