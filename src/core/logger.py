import logging
from logging.handlers import RotatingFileHandler

from src.core.config import settings

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"


def configure_logging():
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    console_handler = logging.StreamHandler()
    file_handler = RotatingFileHandler(
        "app.log", maxBytes=10_000_000, backupCount=5, encoding="utf-8"
    )

    formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
