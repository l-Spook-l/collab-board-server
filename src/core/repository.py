from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def add(self, obj) -> None:
        self.session.add(obj)

    async def get(self, model, obj_id):
        return await self.session.get(model, obj_id)

    async def delete(self, obj):
        await self.session.delete(obj)
        return obj
