import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.core.exceptions.custom_exceptions import AppError, CooldownError

logger = logging.getLogger(__name__)


def setup_exception_handlers(app: FastAPI):
    @app.exception_handler(AppError)
    async def app_error_handler(
        request: Request,
        exc: AppError,
    ):
        logger.warning(
            str(exc.detail),
            extra={
                "path": request.url.path,
                "method": request.method,
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ):
        logger.exception("Unhandled exception")

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
            },
        )

    @app.exception_handler(CooldownError)
    async def cooldown_handler(request, exc: CooldownError):
        return JSONResponse(
            status_code=429,
            content={
                "detail": exc.detail,
                "seconds_left": exc.seconds_left,
            },
        )
