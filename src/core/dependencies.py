from fastapi import Depends, HTTPException, status

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.service import AuthService
from src.core.database import get_async_session

# from app.core.redis import get_redis_client
from src.core.security import decode_access_token
from src.core.uow import UnitOfWork
from src.users.models import User
from src.users.repository import UserRepository
from src.users.service import UserService

bearer_scheme = HTTPBearer()


def get_uow(session: AsyncSession = Depends(get_async_session)):
    return UnitOfWork(session)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token payload")

    user = await UserRepository(session).get(model=User, obj_id=int(user_id))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    return user


def get_user_service(uow: UnitOfWork = Depends(get_uow)) -> UserService:
    return UserService(uow=uow)


def get_auth_service(
    uow: UnitOfWork = Depends(get_uow),
    user_service: UserService = Depends(get_user_service),
) -> AuthService:
    return AuthService(uow=uow, user_service=user_service)
