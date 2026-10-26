import logging
from copy import deepcopy
from typing import Any

import socketio
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from src.boards.schemas import BoardDocumentSchema
from src.boards.service import BoardService
from src.collaboration.connection_manager import connection_manager
from src.collaboration.schemas import (
    StrokeEndEvent,
    StrokePointsEvent,
    StrokeStartEvent,
)
from src.core.config import settings
from src.core.database import async_session_maker
from src.core.exceptions.custom_exceptions import AppError
from src.core.security import decode_access_token
from src.core.uow import UnitOfWork
from src.users.models import User
from src.users.repository import UserRepository

logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.ALLOWED_ORIGINS,
    logger=settings.DEBUG,
    engineio_logger=settings.DEBUG,
)


def _board_room(board_id: int) -> str:
    return f"board:{board_id}"


async def notify_board_deleted(board_id: int, title: str) -> None:
    sids = await connection_manager.close_board(board_id)
    await sio.emit(
        "board:deleted",
        {"id": board_id, "title": title},
        room=_board_room(board_id),
    )
    for sid in sids:
        await sio.disconnect(sid)


async def _board_context(sid: str) -> tuple[int, dict[str, Any]] | None:
    user = connection_manager.get_user(sid)
    board_id = connection_manager.get_board_id(sid)
    if user is None or board_id is None:
        return None
    return board_id, user


@sio.event
async def connect(sid: str, environ: dict, auth: dict | None = None):
    if not isinstance(auth, dict):
        return False

    token = auth.get("token")
    try:
        board_id = int(auth.get("board_id"))
        payload = decode_access_token(token)
        subject = payload.get("sub")
        if not subject or not str(subject).isdigit():
            return False
        user_id = int(subject)

        async with async_session_maker() as session:
            user = await UserRepository(session).get(model=User, obj_id=user_id)
            if not user:
                return False
            board = await BoardService(UnitOfWork(session)).get_board_for_socket(
                board_id=board_id,
                user_id=user_id,
            )
            document = BoardDocumentSchema.model_validate(board.document).model_dump(
                mode="json"
            )
            user_data = {"id": user.id, "name": user.name, "email": user.email}
            board_data = {
                "id": board.id,
                "title": board.title,
                "owner_id": board.owner_id,
                "revision": board.revision,
            }

        room, _ = await connection_manager.connect(
            board_id=board_id,
            sid=sid,
            user=user_data,
            document=document,
            revision=board_data["revision"],
        )
        await sio.save_session(sid, {"user": user_data, "board": board_data})
        await sio.enter_room(sid, _board_room(board_id))
        async with room.lock:
            board_data["revision"] = room.revision
            presence = connection_manager.presence(room)
            await sio.emit(
                "board:state",
                {
                    "board": board_data,
                    "document": deepcopy(room.document),
                    "presence": presence,
                    "dirty": room.dirty,
                },
                to=sid,
            )
            await sio.emit(
                "board:presence",
                {"users": presence},
                room=_board_room(board_id),
            )
        return True
    except (AppError, ValidationError, SQLAlchemyError, TypeError, ValueError) as error:
        logger.info("Socket.IO connection rejected: %s", type(error).__name__)
        return False


@sio.event
async def disconnect(sid: str, reason: str | None = None):
    board_id, _ = await connection_manager.disconnect(sid)
    if board_id is not None:
        room = connection_manager.get_room(board_id)
        if room is not None:
            async with room.lock:
                await sio.emit(
                    "board:presence",
                    {"users": connection_manager.presence(room)},
                    room=_board_room(board_id),
                )


@sio.on("stroke:start")
async def stroke_start(sid: str, payload: dict):
    context = await _board_context(sid)
    if context is None:
        return
    board_id, user = context
    try:
        event = StrokeStartEvent.model_validate(payload)
    except ValidationError:
        return
    room = connection_manager.get_room(board_id)
    if room is None:
        return

    async with room.lock:
        if any(stroke["id"] == event.stroke_id for stroke in room.document["strokes"]):
            return
        stroke = {
            "id": event.stroke_id,
            "color": event.color,
            "width": event.width,
            "points": [event.point.model_dump(mode="json")],
            "user_id": user["id"],
        }
        room.document["strokes"].append(stroke)
        room.dirty = True
        await sio.emit(
            "stroke:start",
            {**event.model_dump(mode="json"), "user_id": user["id"]},
            room=_board_room(board_id),
            skip_sid=sid,
        )


@sio.on("stroke:points")
async def stroke_points(sid: str, payload: dict):
    context = await _board_context(sid)
    if context is None:
        return
    board_id, user = context
    try:
        event = StrokePointsEvent.model_validate(payload)
    except ValidationError:
        return
    room = connection_manager.get_room(board_id)
    if room is None:
        return

    async with room.lock:
        stroke = next(
            (stroke for stroke in room.document["strokes"] if stroke["id"] == event.stroke_id),
            None,
        )
        if not stroke or stroke["user_id"] != user["id"]:
            return
        points = [point.model_dump(mode="json") for point in event.points]
        stroke["points"].extend(points)
        room.dirty = True
        await sio.emit(
            "stroke:points",
            {**event.model_dump(mode="json"), "user_id": user["id"]},
            room=_board_room(board_id),
            skip_sid=sid,
        )


@sio.on("stroke:end")
async def stroke_end(sid: str, payload: dict):
    context = await _board_context(sid)
    if context is None:
        return
    board_id, user = context
    try:
        event = StrokeEndEvent.model_validate(payload)
    except ValidationError:
        return
    room = connection_manager.get_room(board_id)
    if room is None:
        return
    async with room.lock:
        stroke = next(
            (stroke for stroke in room.document["strokes"] if stroke["id"] == event.stroke_id),
            None,
        )
        if not stroke or stroke["user_id"] != user["id"]:
            return
        await sio.emit(
            "stroke:end",
            event.model_dump(mode="json"),
            room=_board_room(board_id),
            skip_sid=sid,
        )


@sio.on("canvas:clear")
async def clear_canvas(sid: str, payload: dict | None = None):
    context = await _board_context(sid)
    if context is None:
        return
    board_id, _ = context
    room = connection_manager.get_room(board_id)
    if room is None:
        return
    async with room.lock:
        room.document["strokes"] = []
        room.dirty = True
        await sio.emit("canvas:clear", {}, room=_board_room(board_id), skip_sid=sid)


@sio.on("board:save")
async def save_board(sid: str, payload: dict | None = None):
    context = await _board_context(sid)
    if context is None:
        return {"ok": False, "error": "Connection is not authorized"}
    board_id, user = context
    room = connection_manager.get_room(board_id)
    if room is None:
        return {"ok": False, "error": "Board session has expired; reconnect"}

    async with room.lock:
        document = deepcopy(room.document)
        try:
            async with async_session_maker() as session:
                revision = await BoardService(UnitOfWork(session)).save_document(
                    board_id=board_id,
                    user_id=user["id"],
                    document=document,
                )
        except (AppError, ValidationError, SQLAlchemyError, TypeError, ValueError):
            logger.exception("Could not save board %s", board_id)
            return {"ok": False, "error": "Could not save the board"}
        room.revision = revision
        room.dirty = False
        result = {"ok": True, "revision": revision, "dirty": False}
        await sio.emit("board:saved", result, room=_board_room(board_id))
    return result
