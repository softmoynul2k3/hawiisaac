from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from tortoise.transactions import in_transaction

from app.auth import login_required, staff_required, superuser_required, permission_required
from app.config import settings
from applications.user.models import User
from applications.user.subscription import Plan, SubscriptionStatus, UserPlan

router = APIRouter(prefix="/subscription", tags=["Subscription"])


class CheckoutSessionIn(BaseModel):
    plan_id: str
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class StripePlanSyncIn(BaseModel):
    plan_id: str
    currency: str = "usd"
    interval: str = "month"
    interval_count: int = 1


class CreatePlanIn(BaseModel):
    name: str
    description: Optional[str] = None
    duration_days: int = 30
    price: Decimal = Decimal("0.0")

    
    features: Optional[List[str]] = []
    auto_sync_stripe: bool = True
    currency: str = "usd"
    interval: str = "month"
    interval_count: int = 1


class ChangePlanStatusIn(BaseModel):
    is_active: bool


def _require_stripe_config() -> None:
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe secret key is not configured")
    stripe.api_key = settings.STRIPE_SECRET_KEY


def _validate_price_cycle(currency: str, interval: str, interval_count: int) -> tuple[str, str]:
    normalized_currency = currency.lower().strip()
    normalized_interval = interval.lower().strip()

    if normalized_interval not in {"day", "week", "month", "year"}:
        raise HTTPException(status_code=400, detail="interval must be one of: day, week, month, year")
    if interval_count < 1:
        raise HTTPException(status_code=400, detail="interval_count must be >= 1")
    if len(normalized_currency) != 3:
        raise HTTPException(status_code=400, detail="currency must be a 3-letter ISO code (example: usd)")

    return normalized_currency, normalized_interval


async def _sync_plan_to_stripe_internal(
    plan: Plan,
    currency: str,
    interval: str,
    interval_count: int,
) -> Plan:
    _require_stripe_config()
    currency, interval = _validate_price_cycle(currency, interval, interval_count)

    if plan.price is None:
        raise HTTPException(status_code=400, detail="Plan price is required")

    unit_amount = int(round(float(plan.price) * 100))
    if unit_amount <= 0:
        raise HTTPException(status_code=400, detail="Plan price must be greater than 0")

    if plan.stripe_product_id:
        product = await run_in_threadpool(
            stripe.Product.modify,
            plan.stripe_product_id,
            name=plan.name,
            description=plan.description or "",
            metadata={"plan_id": str(plan.id)},
        )
    else:
        product = await run_in_threadpool(
            stripe.Product.create,
            name=plan.name,
            description=plan.description or "",
            metadata={"plan_id": str(plan.id)},
        )
        plan.stripe_product_id = product.id

    price = await run_in_threadpool(
        stripe.Price.create,
        product=plan.stripe_product_id,
        unit_amount=unit_amount,
        currency=currency,
        recurring={"interval": interval, "interval_count": interval_count},
        metadata={"plan_id": str(plan.id)},
    )
    plan.stripe_price_id = price.id
    await plan.save()
    return plan


def _stripe_ts_to_datetime(ts: int | None) -> datetime | None:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _status_from_stripe(status: str | None) -> SubscriptionStatus:
    if status in {"active", "trialing"}:
        return SubscriptionStatus.ACTIVE
    if status in {"canceled", "incomplete_expired"}:
        return SubscriptionStatus.CANCELLED
    return SubscriptionStatus.PAUSED


async def _sync_user_plan_from_subscription(
    stripe_subscription: dict[str, Any],
    user_plan: UserPlan | None = None,
    user_id: str | None = None,
) -> UserPlan | None:
    customer_id = stripe_subscription.get("customer")
    subscription_id = stripe_subscription.get("id")
    items = stripe_subscription.get("items", {}).get("data", [])
    price_id = items[0].get("price", {}).get("id") if items else None

    if user_plan is None and user_id:
        user_plan = await UserPlan.get_or_none(user_id=user_id).prefetch_related("plan")
    if user_plan is None and subscription_id:
        user_plan = await UserPlan.get_or_none(stripe_subscription_id=subscription_id).prefetch_related("plan")
    if user_plan is None and customer_id:
        user_plan = await UserPlan.get_or_none(stripe_customer_id=customer_id).prefetch_related("plan")
    if user_plan is None:
        return None

    if price_id:
        plan = await Plan.get_or_none(stripe_price_id=price_id)
        if plan:
            user_plan.plan = plan
            user_plan._sync_with_plan()

    user_plan.stripe_customer_id = customer_id
    user_plan.stripe_subscription_id = subscription_id
    user_plan.stripe_price_id = price_id

    user_plan.started_at = _stripe_ts_to_datetime(stripe_subscription.get("current_period_start")) or user_plan.started_at
    user_plan.current_period_end = _stripe_ts_to_datetime(stripe_subscription.get("current_period_end"))
    user_plan.cancel_at_period_end = bool(stripe_subscription.get("cancel_at_period_end"))

    mapped_status = _status_from_stripe(stripe_subscription.get("status"))
    user_plan.status = mapped_status
    user_plan.auto_renewal = mapped_status != SubscriptionStatus.CANCELLED and not user_plan.cancel_at_period_end

    await user_plan.save()
    return user_plan


@router.post(
    "/plans/create",
    dependencies=[Depends(superuser_required)],
)
async def create_plan(payload: CreatePlanIn):
    plan_name = payload.name.strip()
    if not plan_name:
        raise HTTPException(status_code=400, detail="Plan name is required")
    if payload.duration_days <= 0:
        raise HTTPException(status_code=400, detail="duration_days must be greater than 0")
    if payload.price < 0:
        raise HTTPException(status_code=400, detail="price cannot be negative")
    if payload.disputes_per_month is not None and payload.disputes_per_month < 0:
        raise HTTPException(status_code=400, detail="disputes_per_month cannot be negative")
    if payload.ai_token is not None and payload.ai_token < 0:
        raise HTTPException(status_code=400, detail="ai_token cannot be negative")

    if await Plan.filter(name=plan_name).exists():
        raise HTTPException(status_code=400, detail="Plan with this name already exists")

    async with in_transaction():
        plan = await Plan.create(
            name=plan_name,
            description=payload.description,
            duration_days=payload.duration_days,
            price=payload.price,
            basic_dispute_generation=payload.basic_dispute_generation,
            unlimited_disputes=payload.unlimited_disputes,
            disputes_per_month=payload.disputes_per_month,
            email_support=payload.email_support,
            priority_email_support=payload.priority_email_support,
            phone_support_24_7=payload.phone_support_24_7,
            dedicated_account_manager=payload.dedicated_account_manager,
            access_basic_modules=payload.access_basic_modules,
            access_all_modules=payload.access_all_modules,
            ai_task_recommendations=payload.ai_task_recommendations,
            advanced_analytics=payload.advanced_analytics,
            regular_task_alerts=payload.regular_task_alerts,
            ai_token=payload.ai_token,
        )

    if payload.auto_sync_stripe:
        try:
            plan = await _sync_plan_to_stripe_internal(
                plan=plan,
                currency=payload.currency,
                interval=payload.interval,
                interval_count=payload.interval_count,
            )
        except Exception:
            # Keep DB and Stripe in sync: remove newly created plan if auto-sync fails.
            async with in_transaction():
                await plan.delete()
            raise

    return {
        "detail": "Plan created and synced to Stripe successfully" if payload.auto_sync_stripe else "Plan created successfully",
        "plan": {
            "id": str(plan.id),
            "name": plan.name,
            "description": plan.description,
            "price": str(plan.price) if plan.price is not None else None,
            "duration_days": plan.duration_days,
            "stripe_product_id": plan.stripe_product_id,
            "stripe_price_id": plan.stripe_price_id,
        },
    }


@router.post("/checkout-session")
async def create_checkout_session(payload: CheckoutSessionIn, user: User = Depends(login_required)):
    _require_stripe_config()

    plan = await Plan.get_or_none(id=payload.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if not plan.is_active:
        raise HTTPException(status_code=400, detail="This plan is inactive")
    if not plan.stripe_price_id:
        raise HTTPException(status_code=400, detail="Stripe price is not set for this plan")

    user_plan = await UserPlan.get_or_none(user_id=user.id).prefetch_related("plan")
    if not user_plan:
        user_plan = await UserPlan.create(user=user)

    customer_id = user_plan.stripe_customer_id
    if not customer_id:
        customer = await run_in_threadpool(
            stripe.Customer.create,
            email=user.email,
            name=f"{user.first_name} {user.last_name}",
            metadata={"user_id": str(user.id)},
        )
        customer_id = customer.id
        user_plan.stripe_customer_id = customer_id
        await user_plan.save()

    success_url = payload.success_url or f"{settings.FRONTEND_URL.rstrip('/')}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = payload.cancel_url or f"{settings.FRONTEND_URL.rstrip('/')}/billing/cancel"

    session = await run_in_threadpool(
        stripe.checkout.Session.create,
        mode="subscription",
        customer=customer_id,
        success_url=success_url,
        cancel_url=cancel_url,
        line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
        metadata={
            "user_id": str(user.id),
            "plan_id": str(plan.id),
        },
        subscription_data={
            "metadata": {
                "user_id": str(user.id),
                "plan_id": str(plan.id),
            }
        },
    )

    return {
        "session_id": session.id,
        "checkout_url": session.url,
    }


@router.post("/webhook")
async def stripe_webhook(request: Request):
    _require_stripe_config()

    webhook_secret = settings.STRIPE_WEBHOOK_SECRET or settings.STRIPE_ENDPOINT_SECRET
    if not webhook_secret:
        raise HTTPException(status_code=500, detail="Stripe webhook secret is not configured")

    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    try:
        event = await run_in_threadpool(
            stripe.Webhook.construct_event,
            payload,
            signature,
            webhook_secret,
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Stripe payload")

    event_type = event.get("type")
    event_obj = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        user_id = event_obj.get("metadata", {}).get("user_id")
        plan_id = event_obj.get("metadata", {}).get("plan_id")
        customer_id = event_obj.get("customer")
        subscription_id = event_obj.get("subscription")

        user_plan = None
        if user_id:
            user_plan = await UserPlan.get_or_none(user_id=user_id).prefetch_related("plan")
        if user_plan is None and customer_id:
            user_plan = await UserPlan.get_or_none(stripe_customer_id=customer_id).prefetch_related("plan")

        if user_plan:
            user_plan.stripe_customer_id = customer_id or user_plan.stripe_customer_id
            if plan_id:
                plan = await Plan.get_or_none(id=plan_id)
                if plan:
                    user_plan.plan = plan
                    user_plan._sync_with_plan()
            await user_plan.save()

            if subscription_id:
                stripe_subscription = await run_in_threadpool(stripe.Subscription.retrieve, subscription_id)
                await _sync_user_plan_from_subscription(stripe_subscription, user_plan=user_plan, user_id=user_id)

    elif event_type in {"customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"}:
        await _sync_user_plan_from_subscription(event_obj)

    elif event_type in {"invoice.paid", "invoice.payment_failed"}:
        subscription_id = event_obj.get("subscription")
        if subscription_id:
            stripe_subscription = await run_in_threadpool(stripe.Subscription.retrieve, subscription_id)
            await _sync_user_plan_from_subscription(stripe_subscription)

    return {"received": True}


@router.get("/me")
async def my_subscription(user: User = Depends(login_required)):
    user_plan = await UserPlan.get_or_none(user_id=user.id).prefetch_related("plan")
    if not user_plan:
        return {"subscription": None}

    return {
        "subscription": {
            "id": str(user_plan.id),
            "status": user_plan.status,
            "auto_renewal": user_plan.auto_renewal,
            "cancel_at_period_end": user_plan.cancel_at_period_end,
            "started_at": user_plan.started_at.isoformat() if user_plan.started_at else None,
            "current_period_end": user_plan.current_period_end.isoformat() if user_plan.current_period_end else None,
            "plan": {
                "id": str(user_plan.plan.id) if user_plan.plan else None,
                "name": user_plan.plan.name if user_plan.plan else None,
                "price": str(user_plan.plan.price) if user_plan.plan else None,
                "duration_days": user_plan.plan.duration_days if user_plan.plan else None,
            },
            "stripe_customer_id": user_plan.stripe_customer_id,
            "stripe_subscription_id": user_plan.stripe_subscription_id,
        }
    }


@router.get("/plans")
async def list_plans():
    plans = (
        await Plan.filter(
            is_active=True,
        )
        .order_by("price")
    )
    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>", plans)
    return {
        "plans": [
            {
                "id": str(plan.id),
                "name": plan.name,
                "description": plan.description,
                "price": str(plan.price) if plan.price is not None else None,
                "duration_days": plan.duration_days,
                "is_active": plan.is_active,
            }
            for plan in plans
        ]
    }


@router.get("/my-plan")
async def get_my_plan(user: User = Depends(login_required)):
    user_plan = await UserPlan.get_or_none(user_id=user.id).prefetch_related("plan")
    if not user_plan or not user_plan.plan:
        return {"plan": None}

    plan = user_plan.plan
    return {
        "plan": {
            "id": str(plan.id),
            "name": plan.name,
            "description": plan.description,
            "price": str(plan.price) if plan.price is not None else None,
            "duration_days": plan.duration_days,
            "status": user_plan.status,
            "auto_renewal": user_plan.auto_renewal,
            "cancel_at_period_end": user_plan.cancel_at_period_end,
            "started_at": user_plan.started_at.isoformat() if user_plan.started_at else None,
            "current_period_end": user_plan.current_period_end.isoformat() if user_plan.current_period_end else None,
            "stripe_price_id": plan.stripe_price_id,
        }
    }


@router.get("/payment-history")
async def payment_history(limit: int = 20, user: User = Depends(login_required)):
    _require_stripe_config()

    user_plan = await UserPlan.get_or_none(user_id=user.id)
    if not user_plan or not user_plan.stripe_customer_id:
        return {"payments": []}

    invoices = await run_in_threadpool(
        stripe.Invoice.list,
        customer=user_plan.stripe_customer_id,
        limit=min(max(limit, 1), 100),
    )

    return {
        "payments": [
            {
                "invoice_id": inv.get("id"),
                "amount_paid": (inv.get("amount_paid") or 0) / 100,
                "amount_due": (inv.get("amount_due") or 0) / 100,
                "currency": (inv.get("currency") or "").upper(),
                "status": inv.get("status"),
                "created_at": datetime.fromtimestamp(inv.get("created"), tz=timezone.utc).isoformat() if inv.get("created") else None,
                "invoice_pdf": inv.get("invoice_pdf"),
                "hosted_invoice_url": inv.get("hosted_invoice_url"),
            }
            for inv in invoices.get("data", [])
        ]
    }


@router.post("/cancel")
async def cancel_subscription(user: User = Depends(login_required)):
    _require_stripe_config()

    user_plan = await UserPlan.get_or_none(user_id=user.id)
    if not user_plan or not user_plan.stripe_subscription_id:
        raise HTTPException(status_code=404, detail="No active Stripe subscription found")

    stripe_subscription = await run_in_threadpool(
        stripe.Subscription.modify,
        user_plan.stripe_subscription_id,
        cancel_at_period_end=True,
    )
    await _sync_user_plan_from_subscription(stripe_subscription, user_plan=user_plan, user_id=str(user.id))

    return {"detail": "Subscription will be canceled at period end"}


@router.post("/resume")
async def resume_subscription(user: User = Depends(login_required)):
    _require_stripe_config()

    user_plan = await UserPlan.get_or_none(user_id=user.id)
    if not user_plan or not user_plan.stripe_subscription_id:
        raise HTTPException(status_code=404, detail="No Stripe subscription found")

    stripe_subscription = await run_in_threadpool(
        stripe.Subscription.modify,
        user_plan.stripe_subscription_id,
        cancel_at_period_end=False,
    )
    await _sync_user_plan_from_subscription(stripe_subscription, user_plan=user_plan, user_id=str(user.id))

    return {"detail": "Subscription resumed successfully"}


@router.post(
    "/admin/sync-plan-to-stripe",
    dependencies=[Depends(staff_required)],
)
async def sync_plan_to_stripe(payload: StripePlanSyncIn):
    plan = await Plan.get_or_none(id=payload.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan = await _sync_plan_to_stripe_internal(
        plan=plan,
        currency=payload.currency,
        interval=payload.interval,
        interval_count=payload.interval_count,
    )

    return {
        "detail": "Plan synced to Stripe successfully",
        "plan_id": str(plan.id),
        "stripe_product_id": plan.stripe_product_id,
        "stripe_price_id": plan.stripe_price_id,
    }


@router.patch(
    "/admin/plans/{plan_id}/status",
    dependencies=[Depends(superuser_required)],
)
async def change_plan_status(plan_id: str, payload: ChangePlanStatusIn):
    plan = await Plan.get_or_none(id=plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    stripe_synced = False
    if plan.stripe_product_id or plan.stripe_price_id:
        _require_stripe_config()
        try:
            # Stripe activation order: product first, then price.
            # Stripe deactivation order: price first, then product.
            if payload.is_active:
                if plan.stripe_product_id:
                    await run_in_threadpool(
                        stripe.Product.modify,
                        plan.stripe_product_id,
                        active=True,
                    )
                if plan.stripe_price_id:
                    await run_in_threadpool(
                        stripe.Price.modify,
                        plan.stripe_price_id,
                        active=True,
                    )
            else:
                if plan.stripe_price_id:
                    await run_in_threadpool(
                        stripe.Price.modify,
                        plan.stripe_price_id,
                        active=False,
                    )
                if plan.stripe_product_id:
                    await run_in_threadpool(
                        stripe.Product.modify,
                        plan.stripe_product_id,
                        active=False,
                    )
            stripe_synced = True
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=502, detail=f"Stripe sync failed: {str(e)}")

    async with in_transaction():
        plan.is_active = payload.is_active
        await plan.save()

    return {
        "detail": "Plan status updated successfully",
        "plan_id": str(plan.id),
        "is_active": plan.is_active,
        "stripe_synced": stripe_synced,
    }


@router.delete(
    "/admin/plans/{plan_id}",
    dependencies=[Depends(superuser_required)],
)
async def delete_plan(plan_id: str):
    plan = await Plan.get_or_none(id=plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    stripe_cleanup = {
        "price_deactivated": False,
        "product_deleted": False,
        "product_deactivated": False,
    }
    stripe_errors: list[str] = []

    if plan.stripe_price_id or plan.stripe_product_id:
        _require_stripe_config()

    if plan.stripe_price_id:
        try:
            await run_in_threadpool(
                stripe.Price.modify,
                plan.stripe_price_id,
                active=False,
            )
            stripe_cleanup["price_deactivated"] = True
        except stripe.error.InvalidRequestError:
            # Already removed or invalid on Stripe side.
            stripe_cleanup["price_deactivated"] = True
        except stripe.error.StripeError as e:
            stripe_errors.append(f"price_deactivate_failed: {str(e)}")

    if plan.stripe_product_id:
        try:
            await run_in_threadpool(
                stripe.Product.delete,
                plan.stripe_product_id,
            )
            stripe_cleanup["product_deleted"] = True
        except stripe.error.InvalidRequestError:
            stripe_cleanup["product_deleted"] = True
        except stripe.error.StripeError:
            # If Stripe doesn't allow hard delete, archive product.
            try:
                await run_in_threadpool(
                    stripe.Product.modify,
                    plan.stripe_product_id,
                    active=False,
                )
                stripe_cleanup["product_deactivated"] = True
            except stripe.error.InvalidRequestError:
                stripe_cleanup["product_deactivated"] = True
            except stripe.error.StripeError as e:
                stripe_errors.append(f"product_cleanup_failed: {str(e)}")

    if stripe_errors:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Stripe cleanup failed. Local plan was not deleted.",
                "stripe_errors": stripe_errors,
                "stripe_cleanup": stripe_cleanup,
            },
        )

    async with in_transaction():
        await plan.delete()

    return {
        "detail": "Plan deleted successfully",
        "stripe_cleanup": stripe_cleanup,
    }
