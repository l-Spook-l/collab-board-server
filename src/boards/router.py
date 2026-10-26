from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.boards.schemas import (
    BoardCreateRequestSchema,
    BoardDeleteResponseSchema,
    BoardInviteRequestSchema,
    BoardInviteResponseSchema,
    BoardListResponseSchema,
    BoardResponseSchema,
)
from src.boards.service import BoardService
from src.core.dependencies import get_board_service, get_current_user
from src.collaboration.websocket import notify_board_deleted
from src.users.models import User

router = APIRouter(prefix="/boards", tags=["boards"])
CurrentUserDep = Annotated[User, Depends(get_current_user)]
BoardServiceDep = Annotated[BoardService, Depends(get_board_service)]


@router.post("/", response_model=BoardResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_board(
    data: BoardCreateRequestSchema,
    current_user: CurrentUserDep,
    service: BoardServiceDep,
):
    return await service.create_board(owner_id=current_user.id, data=data)


@router.get("/", response_model=BoardListResponseSchema)
async def list_boards(
    current_user: CurrentUserDep,
    service: BoardServiceDep,
):
    return {"boards": await service.list_boards(user_id=current_user.id)}


@router.get("/{board_id}", response_model=BoardResponseSchema)
async def get_board(
    board_id: int,
    current_user: CurrentUserDep,
    service: BoardServiceDep,
):
    return await service.get_board(board_id=board_id, user_id=current_user.id)


@router.delete("/{board_id}", response_model=BoardDeleteResponseSchema)
async def delete_board(
    board_id: int,
    current_user: CurrentUserDep,
    service: BoardServiceDep,
):
    deleted_board = await service.delete_board(
        board_id=board_id,
        owner_id=current_user.id,
    )
    await notify_board_deleted(board_id=deleted_board.id, title=deleted_board.title)
    return deleted_board


@router.post(
    "/{board_id}/members",
    response_model=BoardInviteResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def invite_board_member(
    board_id: int,
    data: BoardInviteRequestSchema,
    current_user: CurrentUserDep,
    service: BoardServiceDep,
):
    return await service.invite_by_email(
        board_id=board_id,
        owner_id=current_user.id,
        email=str(data.email),
    )
