import logging
import secrets

from sqlalchemy.exc import IntegrityError

from src.auth.schemas import RegisterRequestSchema
from src.auth.utils import get_auth0_public_key
from src.core.config import settings
from src.core.exceptions.custom_exceptions import (
    InvalidCredentialsError,
    UserCreateError,
    MissingEmailInTokenError,
)
from src.core.security import verify_password, create_access_token, decode_auth0_token
from src.core.uow import UnitOfWork
from src.users.models import User
from src.users.schemas import UserCreateRequestSchema
from src.users.service import UserService

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, uow: UnitOfWork, user_service: UserService):
        self.uow = uow
        self.user_service = user_service

    async def register(self, data: RegisterRequestSchema) -> User:
        user_data = UserCreateRequestSchema(
            email=data.email,
            name=data.name,
            password=data.password,
        )

        return await self.user_service.create_user(data=user_data)

    async def login(self, email: str, password: str) -> str:
        user = await self.uow.users.get_user_by_email(email=email)
        if not user or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()

        token = create_access_token(
            {
                "sub": str(user.id),
                "email": user.email,
            }
        )

        logger.info("User logged in", extra={"user_id": user.id, "email": user.email})
        return token

    async def login_auth0(self, auth0_token: str) -> str:
        data_token = await self._verify_auth0_token(auth0_token)
        email = data_token.get("email")
        name = data_token.get("name")

        user = await self.uow.users.get_user_by_email(email=email)
        if not user:
            user = await self._create_user_from_auth0(email=email, username=name)
            logger.info("Auto-created user from Auth0", extra={"email": email})
        else:
            logger.info("Auth0 login", extra={"user_id": user.id, "email": user.email})

        token = create_access_token(
            {
                "sub": str(user.id),
                "email": user.email,
            }
        )
        return token

    @staticmethod
    async def _verify_auth0_token(token: str) -> dict:
        jwks = await get_auth0_public_key()
        payload = decode_auth0_token(token=token, jwks=jwks)

        email = payload.get(f"{settings.AUTH0_NAMESPACE}email") or payload.get("email")
        name = payload.get(f"{settings.AUTH0_NAMESPACE}name") or payload.get("name")
        if not email:
            logger.warning("Required email claim is missing from token")
            raise MissingEmailInTokenError()

        if not name:
            name = email.split("@")[0]
            logger.info(
                "Name field is missing in token, using email prefix as fallback"
            )
        return {"email": email, "name": name}

    async def _create_user_from_auth0(self, email: str, username: str) -> User:
        new_user = User(
            email=email,
            name=username,
            hashed_password=secrets.token_hex(32),
        )
        try:
            async with self.uow:
                self.uow.users.add(obj=new_user)
        except IntegrityError as e:
            logger.error(
                f"Database error during Auth0 user creation: {e}", exc_info=True
            )
            raise UserCreateError()

        return new_user
