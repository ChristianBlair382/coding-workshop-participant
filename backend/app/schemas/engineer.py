from pydantic import BaseModel, ConfigDict, Field

from app.orm_models.enums import ENGINEER_FIELD, ENGINEER_STATUS


class Engineer_Base(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    user_id: int = Field(gt=0)
    field: ENGINEER_FIELD = ENGINEER_FIELD.BUILDING
    status: ENGINEER_STATUS = ENGINEER_STATUS.AVAILABLE


class Engineer_Create(Engineer_Base):
    pass


class Engineer_Read(Engineer_Base):
    id: int
    model_config = ConfigDict(from_attributes=True)


class Engineer_Update(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    field: ENGINEER_FIELD | None = None
    status: ENGINEER_STATUS | None = None
