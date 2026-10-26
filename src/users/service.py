import logging

from sqlalchemy.exc import IntegrityError

from src.core.exceptions.custom_exceptions import (
    NoFieldsToUpdateError,
    PermissionDeniedError,
    UserAlreadyExistsError,
    UserCreateError,
    UserDeleteError,
    UserNotFoundError,
    UserUpdateError,
)
from src.core.pagination import PaginationParams
from src.core.security import hash_password
from src.core.uow import UnitOfWork
from src.users.models import User
from src.users.schemas import UserCreateRequestSchema, UserUpdateRequestSchema

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_user(self, data: UserCreateRequestSchema) -> User:
        new_user = User(
            email=data.email,
            name=data.name,
            hashed_password=hash_password(data.password),
        )

        try:
            async with self.uow:
                existing = await self.uow.users.check_user_by_email(data.email)
                if existing:
                    raise UserAlreadyExistsError()

                self.uow.users.add(obj=new_user)
        except IntegrityError as e:
            logger.error(f"Database error during user creation: {e}", exc_info=True)
            raise UserCreateError()

        logger.info(
            "User created", extra={"user_id": new_user.id, "email": new_user.email}
        )

        return new_user

    async def get_users(self, pagination: PaginationParams) -> dict:
        users = await self.uow.users.get_users(
            offset=pagination.offset,
            limit=pagination.size,
        )
        total = await self.uow.users.get_total_count_users()
        return {
            "users": users,
            "page": pagination.page,
            "size": pagination.size,
            "total": total,
        }

    async def get_user_by_id(self, user_id: int) -> dict:
        user = await self.uow.users.get(model=User, obj_id=user_id)
        if not user:
            raise UserNotFoundError()

        return {"user": user}

    async def search_user_by_email(self, email: str) -> User | None:
        user = await self.uow.users.search_user_by_email(email=email)
        if not user:
            raise UserNotFoundError()

        return user

    async def update_user_by_id(
        self, user_id: int, data: UserUpdateRequestSchema, current_user_id: int
    ) -> dict:
        try:
            async with self.uow:
                user = await self.uow.users.get(model=User, obj_id=user_id)
                if not user:
                    raise UserNotFoundError()

                if current_user_id != user_id:
                    logger.warning(
                        "Unauthorized attempt to update user profile",
                        extra={
                            "current_user_id": current_user_id,
                            "target_user_id": user_id,
                        },
                    )
                    raise PermissionDeniedError()

                update_data = data.model_dump(exclude_unset=True)
                if not update_data:
                    raise NoFieldsToUpdateError()

                if "password" in update_data:
                    user.hashed_password = hash_password(update_data.pop("password"))

                for key, value in update_data.items():
                    setattr(user, key, value)

        except IntegrityError as e:
            logger.error(f"Database error during user update: {e}", exc_info=True)
            raise UserUpdateError()

        logger.info(
            "User updated",
            extra={"user_id": user.id, "email": user.email},
        )
        return {"user": user}

    async def delete_user_by_id(self, user_id: int, current_user_id: int) -> None:
        try:
            async with self.uow:
                user = await self.uow.users.get(model=User, obj_id=user_id)
                if not user:
                    raise UserNotFoundError()

                if current_user_id != user_id:
                    logger.warning(
                        "Unauthorized attempt to delete user profile",
                        extra={
                            "current_user_id": current_user_id,
                            "target_user_id": user_id,
                        },
                    )
                    raise PermissionDeniedError()

                await self.uow.users.delete(obj=user)
        except IntegrityError as e:
            logger.error(f"Database error during user deletion: {e}", exc_info=True)
            raise UserDeleteError()

        logger.info(
            "User deleted",
            extra={"user_id": user.id, "email": user.email},
        )
