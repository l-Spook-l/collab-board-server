from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBaseSchema(BaseModel):
    email: EmailStr
    name: str = Field(min_length=3, max_length=50)


class UserCreateRequestSchema(UserBaseSchema):
    password: str = Field(min_length=6)


class UserUpdateRequestSchema(BaseModel):
    name: str | None = Field(None, min_length=3, max_length=50)
    password: str | None = Field(None, min_length=6)

    model_config = ConfigDict(extra="forbid")


class UserResponseSchema(UserBaseSchema):
    id: int

    model_config = ConfigDict(from_attributes=True)


class UsersListResponseSchema(BaseModel):
    users: list[UserResponseSchema]
    page: int
    size: int
    total: int


class UserDetailResponseSchema(BaseModel):
    user: UserResponseSchema
