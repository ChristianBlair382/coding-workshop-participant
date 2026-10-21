from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .floor import Floor
    from .user import User

class Seat(Base):
    __tablename__ = "seats"

    id: Mapped[int] = mapped_column(primary_key=True)
    seat_id: Mapped[str] = mapped_column(String(50))
    occupied_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    floor_id: Mapped[int] = mapped_column(ForeignKey("floors.id"), nullable=False)

    floor: Mapped["Floor"] = relationship(back_populates="seats")
    occupant: Mapped["User | None"] = relationship(back_populates="seats")

    def __repr__(self) -> str:
        return (f"Seat (ID = {self.id}, Name = {self.name}, Location Region = {self.location_region!r}, Capacity = {self.capacity}, Supervisor ID = {self.supervisor_id})")