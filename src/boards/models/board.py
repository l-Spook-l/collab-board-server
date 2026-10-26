from typing import Any

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.core.mixins import TimestampMixin


class Board(Base, TimestampMixin):
    __tablename__ = "board_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("user_table.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(length=100), nullable=False)
    document: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    revision: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
