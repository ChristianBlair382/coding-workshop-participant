from pydantic import BaseModel, ConfigDict, Field


class Floor_Base(BaseModel):
    floor_id: str = Field(min_length=1, max_length=8)
    seat_count: int = Field(ge=0)
    building_id: int = Field(gt=0)


class Floor_Create(Floor_Base):
    pass


class Floor_Read(Floor_Base):
    id: int
    model_config = ConfigDict(from_attributes=True)


class Floor_Update(BaseModel):
    floor_id: str | None = Field(default=None, min_length=1, max_length=8)
    seat_count: int | None = Field(default=None, ge=0)
    building_id: int | None = Field(default=None, gt=0)
