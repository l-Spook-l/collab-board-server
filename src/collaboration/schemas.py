from typing import Annotated

from pydantic import BaseModel, Field

from src.boards.schemas import BoardPointSchema


class StrokeStartEvent(BaseModel):
    stroke_id: str = Field(min_length=1, max_length=64)
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    width: float = Field(gt=0, le=32)
    point: BoardPointSchema


class StrokePointsEvent(BaseModel):
    stroke_id: str = Field(min_length=1, max_length=64)
    points: Annotated[list[BoardPointSchema], Field(min_length=1, max_length=256)]


class StrokeEndEvent(BaseModel):
    stroke_id: str = Field(min_length=1, max_length=64)
