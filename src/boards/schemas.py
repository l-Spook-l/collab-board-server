from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

CANVAS_WIDTH = 1600
CANVAS_HEIGHT = 950


class BoardPointSchema(BaseModel):
    x: float = Field(ge=0, le=CANVAS_WIDTH)
    y: float = Field(ge=0, le=CANVAS_HEIGHT)


class BoardStrokeSchema(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    width: float = Field(gt=0, le=32)
    points: Annotated[list[BoardPointSchema], Field(min_length=1, max_length=100_000)]
    user_id: int | None = None
    # Keep the distinction between an old stroke (missing this field) and an
    # explicitly white pen stroke. The frontend treats legacy white strokes as erasers.
    is_eraser: bool | None = None


class BoardDocumentSchema(BaseModel):
    version: Literal[1] = 1
    width: Literal[1600] = CANVAS_WIDTH
    height: Literal[950] = CANVAS_HEIGHT
    strokes: Annotated[list[BoardStrokeSchema], Field(max_length=10_000)] = Field(
        default_factory=list
    )


class BoardCreateRequestSchema(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    document: BoardDocumentSchema

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Board title cannot be empty")
        return value


class BoardMemberResponseSchema(BaseModel):
    id: int
    email: EmailStr
    name: str | None
    role: str


class BoardResponseSchema(BaseModel):
    id: int
    title: str
    owner_id: int
    owner_name: str | None
    role: str
    revision: int
    document: BoardDocumentSchema
    members: list[BoardMemberResponseSchema]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BoardListItemSchema(BaseModel):
    id: int
    title: str
    owner_id: int
    owner_name: str | None
    revision: int
    role: str
    updated_at: datetime


class BoardListResponseSchema(BaseModel):
    boards: list[BoardListItemSchema]


class BoardInviteRequestSchema(BaseModel):
    email: EmailStr


class BoardInviteResponseSchema(BaseModel):
    id: int
    email: EmailStr
    name: str | None
    role: str = "editor"


class BoardDeleteResponseSchema(BaseModel):
    id: int
    title: str

