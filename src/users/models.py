from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.core.mixins import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "user_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(length=50), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(length=1024), nullable=False)
