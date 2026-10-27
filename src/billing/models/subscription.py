from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.core.mixins import TimestampMixin


class BillingSubscription(Base, TimestampMixin):
    __tablename__ = "billing_subscription_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_table.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    stripe_customer_id: Mapped[str] = mapped_column(
        String(length=255), nullable=False, unique=True
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(length=255), nullable=True, unique=True
    )
    status: Mapped[str] = mapped_column(
        String(length=32), nullable=False, default="free", server_default="free"
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    last_event_created: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
