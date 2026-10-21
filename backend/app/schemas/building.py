from pydantic import BaseModel, ConfigDict, Field

class Building_Base(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    location: str = Field(min_length=1, max_length=50)
    floor_count: int = Field(ge=0)


class Building_Create(Building_Base):
    pass


class Building_Read(Building_Base):
    id: int
    model_config = ConfigDict(from_attributes=True)


class Building_Update(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    location: str | None = Field(default=None, min_length=1, max_length=50)
    model_config = ConfigDict(extra="forbid")
