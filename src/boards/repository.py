from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.boards.models.board import Board
from src.boards.models.board_member import BoardMember
from src.core.repository import BaseRepository
from src.users.models import User


class BoardRepository(BaseRepository):
    async def get_accessible_board(self, board_id: int, user_id: int) -> Board | None:
        membership = select(BoardMember.board_id).where(
            BoardMember.board_id == Board.id,
            BoardMember.user_id == user_id,
        )
        result = await self.session.execute(
            select(Board)
            .where(Board.id == board_id)
            .where(or_(Board.owner_id == user_id, membership.exists()))
        )
        return result.scalar_one_or_none()

    async def get_owned_board(self, board_id: int, owner_id: int) -> Board | None:
        result = await self.session.execute(
            select(Board).where(Board.id == board_id, Board.owner_id == owner_id)
        )
        return result.scalar_one_or_none()

    async def get_owned_board_for_update(
        self, board_id: int, owner_id: int
    ) -> Board | None:
        result = await self.session.execute(
            select(Board)
            .where(Board.id == board_id, Board.owner_id == owner_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def count_owned_boards(self, owner_id: int) -> int:
        result = await self.session.scalar(
            select(func.count(Board.id)).where(Board.owner_id == owner_id)
        )
        return int(result or 0)

    async def count_invited_members(self, board_id: int) -> int:
        result = await self.session.scalar(
            select(func.count(BoardMember.user_id)).where(
                BoardMember.board_id == board_id
            )
        )
        return int(result or 0)

    async def list_accessible_boards(self, user_id: int) -> list[tuple[Board, str | None]]:
        result = await self.session.execute(
            select(Board, User.name)
            .join(User, User.id == Board.owner_id)
            .outerjoin(
                BoardMember,
                and_(BoardMember.board_id == Board.id, BoardMember.user_id == user_id),
            )
            .where(or_(Board.owner_id == user_id, BoardMember.user_id == user_id))
            .order_by(Board.updated_at.desc(), Board.id.desc())
        )
        return list(result.all())

    async def get_members(self, board_id: int) -> list[tuple[User, bool]]:
        owner_result = await self.session.execute(
            select(User).join(Board, Board.owner_id == User.id).where(Board.id == board_id)
        )
        owner = owner_result.scalar_one_or_none()
        members_result = await self.session.execute(
            select(User)
            .join(BoardMember, BoardMember.user_id == User.id)
            .where(BoardMember.board_id == board_id)
            .order_by(User.name, User.email)
        )
        members = [(member, False) for member in members_result.scalars().all()]
        if owner:
            members.insert(0, (owner, True))
        return members

    async def get_member(self, board_id: int, user_id: int) -> BoardMember | None:
        return await self.session.get(BoardMember, (board_id, user_id))

    async def add_member_if_missing(
        self, board_id: int, user_id: int, invited_by_id: int
    ) -> None:
        statement = (
            pg_insert(BoardMember)
            .values(
                board_id=board_id,
                user_id=user_id,
                invited_by_id=invited_by_id,
            )
            .on_conflict_do_nothing(index_elements=["board_id", "user_id"])
        )
        await self.session.execute(statement)

