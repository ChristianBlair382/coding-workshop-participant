from datetime import datetime

from pydantic import AliasPath, BaseModel, ConfigDict, Field


class Ticket_Note_Attachment_Base(BaseModel):
    file_url: str = Field(min_length=1)


class Ticket_Note_Attachment_Create(Ticket_Note_Attachment_Base):
    ticket_note_id: int = Field(gt=0)


class Ticket_Note_Attachment_Read(Ticket_Note_Attachment_Base):
    id: int
    ticket_note_id: int
    model_config = ConfigDict(from_attributes=True)


class Ticket_Note_Attachment_Update(BaseModel):
    file_url: str | None = Field(default=None, min_length=1)


class Ticket_Note_Base(BaseModel):
    notes: str | None = None
    incident_ticket_id: int = Field(gt=0)
    author_id: int = Field(gt=0)


class Ticket_Note_Create(BaseModel):
    notes: str | None = None
    incident_ticket_id: int = Field(gt=0)
    attachments: list[Ticket_Note_Attachment_Base] = Field(default_factory=list)


class Ticket_Note_Read(Ticket_Note_Base):
    id: int
    created_at: datetime
    author_username: str = Field(validation_alias=AliasPath("author", "username"))
    attachments: list[Ticket_Note_Attachment_Read] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class Ticket_Note_Update(BaseModel):
    notes: str | None = None
