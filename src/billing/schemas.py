from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class BillingStatusResponseSchema(BaseModel):
    plan: Literal["free", "pro"]
    subscription_status: str | None
    cancel_at_period_end: bool
    current_period_end: datetime | None
    has_billing_account: bool
    owned_boards: int
    max_owned_boards: int | None
    max_invited_people_per_board: int


class BillingUrlResponseSchema(BaseModel):
    url: str
