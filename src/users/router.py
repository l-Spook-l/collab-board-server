from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import EmailStr

from src.core.dependencies import get_current_user, get_user_service
from src.core.exceptions.custom_exceptions import UserNotFoundError
from src.core.pagination import PaginationParams
from src.users.models import User
from src.users.schemas import (
    UserCreateRequestSchema,
    UserDetailResponseSchema,
    UserSearchResponseSchema,
    UserResponseSchema,
    UsersListResponseSchema,
    UserUpdateRequestSchema,
)
from src.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/", response_model=UserResponseSchema, status_code=status.HTTP_201_CREATED
)
async def create_user(
    data: UserCreateRequestSchema,
    service: UserService = Depends(get_user_service),
):
    return await service.create_user(data=data)


@router.get(
    "/",
    response_model=UsersListResponseSchema,
    dependencies=[Depends(get_current_user)],
)
async def get_users(
    pagination: PaginationParams = Depends(),
    service: UserService = Depends(get_user_service),
):
    return await service.get_users(pagination=pagination)


@router.get(
    "/search",
    response_model=UserSearchResponseSchema,
    dependencies=[Depends(get_current_user)],
)
async def search_user_by_email(
    email: Annotated[EmailStr, Query()],
    service: Annotated[UserService, Depends(get_user_service)],
):
    return await service.search_user_by_email(email=str(email))


@router.get(
    "/{user_id}",
    response_model=UserDetailResponseSchema,
    dependencies=[Depends(get_current_user)],
)
async def get_user_by_id(
    user_id: int,
    service: UserService = Depends(get_user_service),
):
    return await service.get_user_by_id(user_id=user_id)


@router.patch("/{user_id}", response_model=UserDetailResponseSchema)
async def update_user_by_id(
    user_id: int,
    data: UserUpdateRequestSchema,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    return await service.update_user_by_id(
        user_id=user_id, data=data, current_user_id=current_user.id
    )


@router.delete("/{user_id}")
async def delete_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    await service.delete_user_by_id(user_id=user_id, current_user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
