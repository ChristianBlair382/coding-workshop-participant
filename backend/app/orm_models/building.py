from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .floor import Floor

class Building(Base):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    location: Mapped[str] = mapped_column(String(50))
    floor_count: Mapped[int] = mapped_column(Integer)

    floors: Mapped[list["Floor"]] = relationship(
        back_populates="building",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"Building (ID = {self.id}, Name = {self.name}, Location = {self.location!r}, Floor Count = {self.floor_count})"