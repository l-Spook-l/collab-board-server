import logging

from src.boards.models.board import Board
from src.boards.schemas import (
    BoardCreateRequestSchema,
    BoardDeleteResponseSchema,
    BoardDocumentSchema,
    BoardInviteResponseSchema,
    BoardListItemSchema,
    BoardResponseSchema,
)
from src.core.exceptions.custom_exceptions import (
    BoardNotFoundError,
    PermissionDeniedError,
    UserNotFoundError,
)
from src.core.uow import UnitOfWork

logger = logging.getLogger(__name__)


class BoardService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_board(
        self, owner_id: int, data: BoardCreateRequestSchema
    ) -> BoardResponseSchema:
        board = Board(
            owner_id=owner_id,
            title=data.title,
            document=data.document.model_dump(mode="json"),
            revision=1,
        )
        async with self.uow:
            self.uow.boards.add(board)
            await self.uow.session.flush()
        logger.info(
            "Board created",
            extra={"board_id": board.id, "owner_id": owner_id},
        )
        return await self.get_board(board_id=board.id, user_id=owner_id)

    async def list_boards(self, user_id: int) -> list[BoardListItemSchema]:
        rows = await self.uow.boards.list_accessible_boards(user_id=user_id)
        return [
            BoardListItemSchema(
                id=board.id,
                title=board.title,
                owner_id=board.owner_id,
                owner_name=owner_name,
                revision=board.revision,
                role="owner" if board.owner_id == user_id else "editor",
                updated_at=board.updated_at,
            )
            for board, owner_name in rows
        ]

    async def get_board(self, board_id: int, user_id: int) -> BoardResponseSchema:
        board = await self.uow.boards.get_accessible_board(
            board_id=board_id, user_id=user_id
        )
        if not board:
            exists = await self.uow.boards.get(model=Board, board_id=board_id)
            if not exists:
                raise BoardNotFoundError()
            raise PermissionDeniedError("You do not have access to this board")

        members = await self.uow.boards.get_members(board_id=board_id)
        owner = next((member for member, is_owner in members if is_owner), None)
        return BoardResponseSchema(
            id=board.id,
            title=board.title,
            owner_id=board.owner_id,
            owner_name=owner.name if owner else None,
            role="owner" if board.owner_id == user_id else "editor",
            revision=board.revision,
            document=BoardDocumentSchema.model_validate(board.document),
            members=[
                {
                    "id": member.id,
                    "email": member.email,
                    "name": member.name,
                    "role": "owner" if is_owner else "editor",
                }
                for member, is_owner in members
            ],
            created_at=board.created_at,
            updated_at=board.updated_at,
        )

    async def get_board_for_socket(self, board_id: int, user_id: int) -> Board:
        board = await self.uow.boards.get_accessible_board(
            board_id=board_id, user_id=user_id
        )
        if not board:
            raise BoardNotFoundError("Board not found or access denied")
        return board

    async def delete_board(
        self, board_id: int, owner_id: int
    ) -> BoardDeleteResponseSchema:
        async with self.uow:
            board = await self.uow.boards.get_owned_board(
                board_id=board_id,
                owner_id=owner_id,
            )
            if not board:
                exists = await self.uow.boards.get(model=Board, obj_id=board_id)
                if not exists:
                    raise BoardNotFoundError()
                logger.warning(
                    "Unauthorized attempt to delete board",
                    extra={"board_id": board_id, "requester_id": owner_id},
                )
                raise PermissionDeniedError("Only the board owner can delete it")

            deleted_board = BoardDeleteResponseSchema(id=board.id, title=board.title)
            await self.uow.boards.delete(board)

        logger.info(
            "Board deleted",
            extra={"board_id": deleted_board.id, "owner_id": owner_id},
        )
        return deleted_board

    async def save_document(
        self, board_id: int, user_id: int, document: dict
    ) -> int:
        async with self.uow:
            board = await self.uow.boards.get_accessible_board(
                board_id=board_id, user_id=user_id
            )
            if not board:
                raise BoardNotFoundError("Board not found or access denied")
            board.document = BoardDocumentSchema.model_validate(document).model_dump(
                mode="json"
            )
            board.revision += 1
            await self.uow.session.flush()
            revision = board.revision
        logger.info(
            "Board saved",
            extra={"board_id": board_id, "user_id": user_id, "revision": revision},
        )
        return revision

    async def invite_by_email(
        self, board_id: int, owner_id: int, email: str
    ) -> BoardInviteResponseSchema:
        async with self.uow:
            board = await self.uow.boards.get_owned_board(
                board_id=board_id, owner_id=owner_id
            )
            if not board:
                exists = await self.uow.boards.get(model=Board, board_id=board_id)
                if not exists:
                    raise BoardNotFoundError()
                logger.warning(
                    "Unauthorized attempt to invite a user to board",
                    extra={"board_id": board_id, "requester_id": owner_id},
                )
                raise PermissionDeniedError("Only the board owner can invite users")

            user = await self.uow.users.search_user_by_email(email=email)
            if not user:
                raise UserNotFoundError("Registered user with this email was not found")
            if user.id == owner_id:
                raise PermissionDeniedError("The board owner already has access")

            await self.uow.boards.add_member_if_missing(
                board_id=board_id,
                user_id=user.id,
                invited_by_id=owner_id,
            )

            invited_member = BoardInviteResponseSchema(
                id=user.id,
                email=user.email,
                name=user.name,
            )

        logger.info(
            "Board member access granted",
            extra={"board_id": board_id, "owner_id": owner_id, "user_id": user.id},
        )
        return invited_member
