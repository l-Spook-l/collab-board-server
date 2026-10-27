from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.billing.models import BillingSubscription
from src.core.repository import BaseRepository


class BillingRepository(BaseRepository):
    async def get_by_user_id(
        self, user_id: int, for_update: bool = False
    ) -> BillingSubscription | None:
        statement = select(BillingSubscription).where(
            BillingSubscription.user_id == user_id
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_customer_id(
        self, customer_id: str, for_update: bool = False
    ) -> BillingSubscription | None:
        statement = select(BillingSubscription).where(
            BillingSubscription.stripe_customer_id == customer_id
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_subscription_id(
        self, subscription_id: str, for_update: bool = False
    ) -> BillingSubscription | None:
        statement = select(BillingSubscription).where(
            BillingSubscription.stripe_subscription_id == subscription_id
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def ensure_customer(
        self, user_id: int, customer_id: str
    ) -> BillingSubscription:
        statement = (
            pg_insert(BillingSubscription)
            .values(user_id=user_id, stripe_customer_id=customer_id, status="free")
            .on_conflict_do_nothing(index_elements=["user_id"])
        )
        await self.session.execute(statement)
        subscription = await self.get_by_user_id(user_id)
        if subscription is None:
            raise RuntimeError("Could not persist the Stripe customer")
        return subscription
