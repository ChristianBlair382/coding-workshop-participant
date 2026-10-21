from datetime import datetime

from pydantic import AliasPath, BaseModel, ConfigDict, Field

from app.orm_models.enums import INCIDENT_TICKET_PRIORITY, INCIDENT_TICKET_STATUS

class Incident_Ticket_Base(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1)
    priority: INCIDENT_TICKET_PRIORITY = INCIDENT_TICKET_PRIORITY.MEDIUM
    status: INCIDENT_TICKET_STATUS = INCIDENT_TICKET_STATUS.OPEN
    assigned_engineer_id: int | None = Field(default=None, gt=0)
    created_by_id: int = Field(gt=0)

class Incident_Ticket_Create(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1)
    priority: INCIDENT_TICKET_PRIORITY = INCIDENT_TICKET_PRIORITY.MEDIUM
    status: INCIDENT_TICKET_STATUS = INCIDENT_TICKET_STATUS.OPEN
    assigned_engineer_id: int | None = Field(default=None, gt=0)

class Incident_Ticket_Read(Incident_Ticket_Base):
    id: int
    created_at: datetime | None
    acknowledged_at: datetime | None
    assigned_at: datetime | None
    completed_at: datetime | None
    created_by_username: str = Field(validation_alias=AliasPath("creator", "username"))
    model_config = ConfigDict(from_attributes=True)

class Incident_Ticket_Update(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, min_length=1)
    priority: INCIDENT_TICKET_PRIORITY | None = None
    status: INCIDENT_TICKET_STATUS | None = None
    assigned_engineer_id: int | None = Field(default=None, gt=0)