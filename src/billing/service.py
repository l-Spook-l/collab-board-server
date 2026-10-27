import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import stripe
from fastapi import HTTPException, status

from src.billing.limits import (
    has_pro_access,
    max_invited_members,
    max_owned_boards,
)
from src.billing.schemas import BillingStatusResponseSchema
from src.core.config import settings
from src.core.exceptions.custom_exceptions import ConflictError
from src.core.uow import UnitOfWork
from src.users.models import User

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY.get_secret_value()


class BillingService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_status(self, user_id: int) -> BillingStatusResponseSchema:
        async with self.uow:
            subscription = await self.uow.billing.get_by_user_id(user_id)
            owned_boards = await self.uow.boards.count_owned_boards(user_id)

        stripe_status = subscription.status if subscription else None
        is_pro = has_pro_access(stripe_status)
        return BillingStatusResponseSchema(
            plan="pro" if is_pro else "free",
            subscription_status=stripe_status,
            cancel_at_period_end=(
                subscription.cancel_at_period_end if subscription else False
            ),
            current_period_end=(
                subscription.current_period_end if subscription else None
            ),
            has_billing_account=subscription is not None,
            owned_boards=owned_boards,
            max_owned_boards=max_owned_boards(stripe_status),
            max_invited_people_per_board=max_invited_members(stripe_status),
        )

    async def create_checkout_session(self, user: User) -> str:
        async with self.uow:
            subscription = await self.uow.billing.get_by_user_id(user.id)
            current_status = subscription.status if subscription else None
            customer_id = (
                subscription.stripe_customer_id if subscription else None
            )

        if has_pro_access(current_status):
            raise ConflictError(
                "Your Pro subscription is already active. Use Manage billing to update it."
            )
        if current_status == "incomplete":
            raise ConflictError(
                "A subscription payment is still being confirmed. Please try again shortly."
            )

        if customer_id is None:
            customer = await self._stripe_call(
                stripe.Customer.create,
                email=user.email,
                name=user.name,
                metadata={"user_id": str(user.id)},
                idempotency_key=f"collabboard-customer-{user.id}",
            )
            customer_id = str(customer.id)
            async with self.uow:
                subscription = await self.uow.billing.ensure_customer(
                    user_id=user.id, customer_id=customer_id
                )
                customer_id = subscription.stripe_customer_id

        frontend_url = settings.FRONTEND_URL.rstrip("/")
        session = await self._stripe_call(
            stripe.checkout.Session.create,
            mode="subscription",
            customer=customer_id,
            line_items=[{"price": settings.STRIPE_PRICE_ID, "quantity": 1}],
            success_url=f"{frontend_url}/profile?checkout=success",
            cancel_url=f"{frontend_url}/profile?checkout=cancelled",
            client_reference_id=str(user.id),
            metadata={"user_id": str(user.id)},
            subscription_data={"metadata": {"user_id": str(user.id)}},
        )
        if not session.url:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Stripe did not return a checkout URL.",
            )
        return str(session.url)

    async def create_portal_session(self, user_id: int) -> str:
        async with self.uow:
            subscription = await self.uow.billing.get_by_user_id(user_id)

        if subscription is None:
            raise ConflictError("No Stripe billing account exists for this user yet.")

        portal_session = await self._stripe_call(
            stripe.billing_portal.Session.create,
            customer=subscription.stripe_customer_id,
            return_url=f"{settings.FRONTEND_URL.rstrip('/')}/profile",
        )
        return str(portal_session.url)

    async def handle_webhook(self, event: Any) -> None:
        event_type = _value(event, "type")
        event_created = int(_value(event, "created") or 0)
        data = _value(event, "data") or {}
        event_object = _value(data, "object") or {}

        if event_type == "checkout.session.completed":
            subscription_id = _stripe_id(_value(event_object, "subscription"))
            if not subscription_id:
                return
            subscription = await self._stripe_call(
                stripe.Subscription.retrieve, subscription_id
            )
            user_id = _parse_user_id(
                _value(event_object, "client_reference_id")
                or _metadata_user_id(event_object)
                or _metadata_user_id(subscription)
            )
            await self._apply_subscription(
                user_id=user_id,
                subscription=subscription,
                event_created=event_created,
            )
            return

        if event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
            "customer.subscription.paused",
            "customer.subscription.resumed",
        }:
            subscription_id = _stripe_id(_value(event_object, "id"))
            if not subscription_id:
                return

            if event_type == "customer.subscription.deleted":
                subscription = event_object
            else:
                # Fetch the current Stripe state so delayed webhook deliveries
                # cannot restore an older status or billing period.
                subscription = await self._stripe_call(
                    stripe.Subscription.retrieve, subscription_id
                )

            await self._apply_subscription(
                user_id=_parse_user_id(_metadata_user_id(subscription)),
                subscription=subscription,
                event_created=event_created,
            )
            return

        if event_type in {"invoice.paid", "invoice.payment_failed"}:
            subscription_id = _invoice_subscription_id(event_object)
            if not subscription_id:
                return
            subscription = await self._stripe_call(
                stripe.Subscription.retrieve, subscription_id
            )
            await self._apply_subscription(
                user_id=_parse_user_id(_metadata_user_id(subscription)),
                subscription=subscription,
                event_created=event_created,
            )

    async def _apply_subscription(
        self,
        user_id: int | None,
        subscription: Any,
        event_created: int,
    ) -> None:
        subscription_id = _stripe_id(_value(subscription, "id"))
        customer_id = _stripe_id(_value(subscription, "customer"))
        if not subscription_id or not customer_id:
            return

        async with self.uow:
            record = await self.uow.billing.get_by_subscription_id(
                subscription_id, for_update=True
            )
            if record is None and user_id is not None:
                record = await self.uow.billing.get_by_user_id(
                    user_id, for_update=True
                )
            if record is None:
                record = await self.uow.billing.get_by_customer_id(
                    customer_id, for_update=True
                )
            if record is None and user_id is not None:
                user = await self.uow.users.get(model=User, obj_id=user_id)
                if user is None:
                    return
                record = await self.uow.billing.ensure_customer(
                    user_id=user_id, customer_id=customer_id
                )
            if record is None or record.stripe_customer_id != customer_id:
                logger.warning(
                    "Stripe subscription event does not match a billing account",
                    extra={"stripe_subscription_id": subscription_id},
                )
                return

            if (
                record.last_event_created is not None
                and event_created < record.last_event_created
            ):
                return

            if (
                record.stripe_subscription_id not in (None, subscription_id)
                and has_pro_access(record.status)
            ):
                # A delayed event from a previous subscription must not replace
                # a newer subscription that currently grants Pro access.
                return

            record.stripe_subscription_id = subscription_id
            record.status = str(_value(subscription, "status") or "free")
            record.current_period_end = _timestamp_datetime(
                _value(subscription, "current_period_end")
                or _first_item_period_end(subscription)
            )
            record.cancel_at_period_end = bool(
                _value(subscription, "cancel_at_period_end")
            )
            record.last_event_created = max(
                event_created, record.last_event_created or 0
            )

    async def _stripe_call(self, function, *args, **kwargs):
        try:
            return await asyncio.to_thread(function, *args, **kwargs)
        except stripe.StripeError as error:
            logger.warning(
                "Stripe API request failed",
                extra={"stripe_error_type": type(error).__name__},
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Stripe billing is temporarily unavailable.",
            ) from error


def _value(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    try:
        return obj[key]
    except (KeyError, TypeError, AttributeError):
        return None


def _stripe_id(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    identifier = _value(value, "id") if value is not None else None
    return str(identifier) if identifier else None


def _metadata_user_id(obj: Any) -> Any:
    return _value(_value(obj, "metadata") or {}, "user_id")


def _parse_user_id(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _timestamp_datetime(timestamp: Any) -> datetime | None:
    if not timestamp:
        return None
    try:
        return datetime.fromtimestamp(int(timestamp), tz=UTC)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _first_item_period_end(subscription: Any) -> Any:
    items = _value(subscription, "items")
    data = _value(items, "data") or []
    return _value(data[0], "current_period_end") if data else None


def _invoice_subscription_id(invoice: Any) -> str | None:
    subscription_id = _stripe_id(_value(invoice, "subscription"))
    if subscription_id:
        return subscription_id
    parent = _value(invoice, "parent")
    details = _value(parent, "subscription_details")
    return _stripe_id(_value(details, "subscription"))
