from typing import Annotated

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from src.billing.schemas import BillingStatusResponseSchema, BillingUrlResponseSchema
from src.billing.service import BillingService
from src.core.config import settings
from src.core.dependencies import get_billing_service, get_current_user
from src.users.models import User

router = APIRouter(prefix="/billing", tags=["billing"])
CurrentUserDep = Annotated[User, Depends(get_current_user)]
BillingServiceDep = Annotated[BillingService, Depends(get_billing_service)]


@router.get("/subscription", response_model=BillingStatusResponseSchema)
async def get_subscription_status(
    current_user: CurrentUserDep,
    service: BillingServiceDep,
):
    return await service.get_status(user_id=current_user.id)


@router.post("/checkout", response_model=BillingUrlResponseSchema)
async def create_checkout_session(
    current_user: CurrentUserDep,
    service: BillingServiceDep,
):
    url = await service.create_checkout_session(user=current_user)
    return BillingUrlResponseSchema(url=url)


@router.post("/portal", response_model=BillingUrlResponseSchema)
async def create_portal_session(
    current_user: CurrentUserDep,
    service: BillingServiceDep,
):
    url = await service.create_portal_session(user_id=current_user.id)
    return BillingUrlResponseSchema(url=url)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    service: BillingServiceDep,
    stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")] = None,
):
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature.")

    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.STRIPE_WEBHOOK_SECRET.get_secret_value(),
        )
    except (ValueError, stripe.SignatureVerificationError) as error:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook.") from error

    await service.handle_webhook(event)
    return {"received": True}
