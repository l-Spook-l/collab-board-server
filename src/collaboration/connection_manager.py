import asyncio
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BoardRoom:
    document: dict[str, Any]
    revision: int
    dirty: bool = False
    participants: dict[str, dict[str, Any]] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    cleanup_task: asyncio.Task | None = None


class ConnectionManager:
    """Process-local collaboration state; run the backend with one worker."""

    def __init__(self) -> None:
        self._rooms: dict[int, BoardRoom] = {}
        self._sid_to_board: dict[str, int] = {}
        self._guard: asyncio.Lock | None = None

    def _get_guard(self) -> asyncio.Lock:
        if self._guard is None:
            self._guard = asyncio.Lock()
        return self._guard

    async def connect(
        self,
        *,
        board_id: int,
        sid: str,
        user: dict[str, Any],
        document: dict[str, Any],
        revision: int,
    ) -> tuple[BoardRoom, dict[str, Any]]:
        async with self._get_guard():
            room = self._rooms.get(board_id)
            if room is None:
                room = BoardRoom(document=deepcopy(document), revision=revision)
                self._rooms[board_id] = room
            if room.cleanup_task:
                room.cleanup_task.cancel()
                room.cleanup_task = None

        async with room.lock:
            room.participants[sid] = user
            self._sid_to_board[sid] = board_id
            return room, self.presence(room)

    async def disconnect(self, sid: str) -> tuple[int | None, list[dict[str, Any]]]:
        board_id = self._sid_to_board.pop(sid, None)
        if board_id is None:
            return None, []
        room = self._rooms.get(board_id)
        if room is None:
            return board_id, []

        async with room.lock:
            room.participants.pop(sid, None)
            presence = self.presence(room)
            if not room.participants:
                # Keep a short grace period for Socket.IO automatic reconnection.
                room.cleanup_task = asyncio.create_task(self._expire_room(board_id, room))
            return board_id, presence

    async def close_board(self, board_id: int) -> list[str]:
        room = self._rooms.get(board_id)
        if room is None:
            return []

        async with room.lock:
            if room.cleanup_task:
                room.cleanup_task.cancel()
                room.cleanup_task = None

            sids = list(room.participants)
            room.participants.clear()
            async with self._get_guard():
                if self._rooms.get(board_id) is room:
                    self._rooms.pop(board_id, None)
                for sid in sids:
                    self._sid_to_board.pop(sid, None)
            return sids

    async def remove_user_from_board(
        self, board_id: int, user_id: int
    ) -> tuple[list[str], list[dict[str, Any]]]:
        room = self._rooms.get(board_id)
        if room is None:
            return [], []

        async with room.lock:
            sids = [
                sid
                for sid, user in room.participants.items()
                if user["id"] == user_id
            ]
            for sid in sids:
                room.participants.pop(sid, None)
            async with self._get_guard():
                for sid in sids:
                    self._sid_to_board.pop(sid, None)

            presence = self.presence(room)
            if not room.participants and room.cleanup_task is None:
                room.cleanup_task = asyncio.create_task(
                    self._expire_room(board_id, room)
                )
            return sids, presence

    async def _expire_room(self, board_id: int, room: BoardRoom) -> None:
        try:
            await asyncio.sleep(300)
            async with room.lock:
                if room.participants:
                    return
                async with self._get_guard():
                    if self._rooms.get(board_id) is room:
                        self._rooms.pop(board_id, None)
        except asyncio.CancelledError:
            return

    def get_room(self, board_id: int) -> BoardRoom | None:
        return self._rooms.get(board_id)

    def get_user(self, sid: str) -> dict[str, Any] | None:
        board_id = self._sid_to_board.get(sid)
        room = self._rooms.get(board_id) if board_id is not None else None
        return room.participants.get(sid) if room else None

    def get_board_id(self, sid: str) -> int | None:
        return self._sid_to_board.get(sid)

    @staticmethod
    def presence(room: BoardRoom) -> list[dict[str, Any]]:
        unique_users: dict[int, dict[str, Any]] = {}
        for participant in room.participants.values():
            unique_users[participant["id"]] = participant
        return list(unique_users.values())


connection_manager = ConnectionManager()
