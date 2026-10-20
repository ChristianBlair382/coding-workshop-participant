from pydantic import BaseModel, ConfigDict, Field

from app.orm_models import USER_ROLE

class User_Base(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    role: USER_ROLE = USER_ROLE.EMP

class User_Create(User_Base):
    password: str = Field(min_length=8)

class User_Read(User_Base):
    id: int
    model_config = ConfigDict(from_attributes=True)

class Permission_Read(BaseModel):
    name: str
    description: str | None = None
    model_config = ConfigDict(from_attributes=True)

class User_Permissions_Read(BaseModel):
    role: USER_ROLE
    permissions: list[Permission_Read]

class Role_Permissions_Read(BaseModel):
    role: USER_ROLE
    permissions: list[Permission_Read]

class User_Update(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=50)
    password: str = Field(min_length=8)
    role: USER_ROLE | None = None

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class Refresh_Token_Request(BaseModel):
    refresh_token: str = Field(min_length=1)