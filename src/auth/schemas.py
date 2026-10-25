from pydantic import BaseModel, EmailStr, Field, ConfigDict


class LoginRequestSchema(BaseModel):
    email: EmailStr
    password: str


class TokenResponseSchema(BaseModel):
    token_type: str = "bearer"
    access_token: str


class Auth0TokenRequestSchema(BaseModel):
    token: str


class RegisterBaseSchema(BaseModel):
    email: EmailStr
    name: str = Field(min_length=3, max_length=50)


class RegisterRequestSchema(RegisterBaseSchema):
    password: str = Field(min_length=6)

    model_config = ConfigDict(extra="forbid")


class RegisterResponseSchema(RegisterBaseSchema):
    id: int

    model_config = ConfigDict(from_attributes=True)
