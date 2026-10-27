from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.repository import BillingRepository
from src.boards.repository import BoardRepository
from src.users.repository import UserRepository


class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(self.session)
        self.boards = BoardRepository(self.session)
        self.billing = BillingRepository(self.session)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.session.rollback()
        else:
            await self.session.commit()
