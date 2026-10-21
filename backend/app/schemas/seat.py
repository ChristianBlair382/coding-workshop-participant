from pydantic import BaseModel, ConfigDict, Field

class Seat_Base(BaseModel):
    seat_id: str = Field(min_length=1, max_length=50)
    occupied_by: int | None = Field(default=None, gt=0)
    floor_id: int = Field(gt=0)

class Seat_Create(Seat_Base):
    pass


class Seat_Bulk_Create(BaseModel):
    occupied_by: list[int | None] = Field(min_length=1, max_length=50)


class Seat_Read(Seat_Base):
    id: int
    model_config = ConfigDict(from_attributes=True)

class Seat_Update(BaseModel):
    seat_id: str | None = Field(default=None, min_length=1, max_length=50)
    occupied_by: int | None = Field(default=None, gt=0)
    floor_id: int | None = Field(default=None, gt=0)
