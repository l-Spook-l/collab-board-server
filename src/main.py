import socketio
from fastapi import FastAPI

from src.auth.router import router as router_auth
from src.billing.router import router as router_billing
from src.boards.router import router as router_boards
from src.collaboration.websocket import sio
from src.core.config import settings
from src.core.cors import setup_cors
from src.core.exceptions.handlers import setup_exception_handlers
from src.users.router import router as router_user

fastapi_app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
)

setup_exception_handlers(fastapi_app)
setup_cors(fastapi_app)

fastapi_app.include_router(router_user)
fastapi_app.include_router(router_auth)
fastapi_app.include_router(router_boards)
fastapi_app.include_router(router_billing)

# Socket.IO handles /socket.io traffic and forwards ordinary HTTP requests to FastAPI.
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
