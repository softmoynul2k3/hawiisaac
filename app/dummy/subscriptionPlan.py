from decimal import Decimal

from tortoise.transactions import in_transaction

from applications.user.subscription import Plan
from routes.user.subscription import _sync_plan_to_stripe_internal
# 👆 change this import to your actual router/service file name


DUMMY_PLANS = [
    {
        "name": "Basic",
        "description": "Free basic access plan",
        "duration_days": 30,
        "price": Decimal("0.00"),
        "features": [
            "5 accesses/month",
            "Basic tracking",
            "Community support",
        ],
        "stripe": None,
    },
    {
        "name": "Pro Monthly",
        "description": "Monthly premium subscription",
        "duration_days": 30,
        "price": Decimal("4.99"),
        "features": [
            "Unlimited access",
            "Advanced tracking",
            "AI workout generator",
            "Advanced analytics",
            "Priority support",
        ],
        "stripe": {
            "currency": "usd",
            "interval": "month",
            "interval_count": 1,
        },
    },
    {
        "name": "Pro Yearly",
        "description": "Yearly premium subscription with savings",
        "duration_days": 365,
        "price": Decimal("24.99"),
        "features": [
            "Everything in Monthly",
            "Save 35%",
            "AI fitness coach",
            "Recovery heatmap",
            "VIP support",
        ],
        "stripe": {
            "currency": "usd",
            "interval": "year",
            "interval_count": 1,
        },
    },
]


async def create_dummy_plans(sync_stripe: bool = True):
    created_count = 0
    updated_count = 0
    stripe_synced_count = 0

    try:
        for item in DUMMY_PLANS:
            stripe_config = item.pop("stripe", None)

            async with in_transaction() as conn:
                plan, created = await Plan.get_or_create(
                    name=item["name"],
                    defaults=item,
                    using_db=conn,
                )

                if created:
                    created_count += 1
                    print(f"[dummy-plan] created: {plan.name}")
                else:
                    updated = False

                    for field, value in item.items():
                        if getattr(plan, field) != value:
                            setattr(plan, field, value)
                            updated = True

                    if updated:
                        await plan.save(using_db=conn)
                        updated_count += 1
                        print(f"[dummy-plan] updated: {plan.name}")

            # Sync only paid plans to Stripe
            if sync_stripe and stripe_config and not plan.stripe_price_id:
                plan = await _sync_plan_to_stripe_internal(
                    plan=plan,
                    currency=stripe_config["currency"],
                    interval=stripe_config["interval"],
                    interval_count=stripe_config["interval_count"],
                )
                stripe_synced_count += 1
                print(f"[dummy-plan] stripe synced: {plan.name} -> {plan.stripe_price_id}")

        print(
            f"[dummy-plan] completed "
            f"(created={created_count}, updated={updated_count}, stripe_synced={stripe_synced_count})"
        )

    except Exception as error:
        print(f"[dummy-plan] failed: {error}")