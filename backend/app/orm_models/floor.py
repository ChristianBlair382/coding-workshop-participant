from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .building import Building
    from .seat import Seat

class Floor(Base):
    __tablename__ = "floors"

    id: Mapped[int] = mapped_column(primary_key=True)
    floor_id: Mapped[str] = mapped_column(String(8))
    seat_count: Mapped[int] = mapped_column(Integer)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"), nullable=False)

    building: Mapped["Building"] = relationship(back_populates="floors")
    seats: Mapped[list["Seat"]] = relationship(
        back_populates="floor",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (f"Floor (ID = {self.id}, Name = {self.name}, Location Region = {self.location_region!r}, Capacity = {self.capacity}, Supervisor ID = {self.supervisor_id})")