from sqlalchemy import exists, func, select

from src.core.repository import BaseRepository
from src.users.models import User


class UserRepository(BaseRepository):
    async def check_user_by_email(self, email: str) -> bool:
        return await self.session.scalar(select(exists().where(User.email == email)))

    async def get_users(self, offset: int, limit: int) -> list[User]:
        result = await self.session.scalars(select(User).offset(offset).limit(limit))
        return list(result.all())

    async def get_total_count_users(self) -> int:
        return await self.session.scalar(select(func.count(User.id)))

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def search_user_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(func.lower(User.email) == email.strip().lower())
        )
        return result.scalar_one_or_none()
