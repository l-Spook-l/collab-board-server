from fastapi import FastAPI

from src.core.cors import setup_cors
from src.users.router import router as router_user
from src.auth.router import router as router_auth
from src.core.exceptions.handlers import setup_exception_handlers

app = FastAPI(
    title="My FastAPI Application",
)

setup_exception_handlers(app)
setup_cors(app)

app.include_router(router_user)
app.include_router(router_auth)
