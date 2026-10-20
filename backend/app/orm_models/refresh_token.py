from __future__ import annotations
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

class Refresh_Token(Base):
    __tablename__ = "refresh_tokens"
    
    DAYS_TILL_EXPIRE: int = 30

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    family_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), default=uuid4, nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return (
            f"Refresh Token (ID: {self.id}, User ID: {self.user_id}, "
            f"Family ID: {self.family_id}, Expires At: {self.expires_at}, "
            f"Revoked At: {self.revoked_at})"
        )