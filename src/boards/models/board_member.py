from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.core.database import Base


class BoardMember(Base):
    __tablename__ = "board_member_table"

    board_id: Mapped[int] = mapped_column(
        ForeignKey("board_table.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_table.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    invited_by_id: Mapped[int] = mapped_column(
        ForeignKey("user_table.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
