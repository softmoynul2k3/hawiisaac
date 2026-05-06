from datetime import datetime, timedelta, timezone
from enum import Enum

from tortoise import models, fields

class SubscriptionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"



class UserPlan(models.Model):
    id = fields.UUIDField(pk=True)

    # Basic Info
    user = fields.OneToOneField("models.User", related_name="subscription", on_delete=fields.CASCADE)
    plan = fields.ForeignKeyField("models.Plan", related_name="plan", on_delete=fields.SET_NULL, null=True)
    pending_plan = fields.ForeignKeyField("models.Plan", related_name="pending_user_plans", on_delete=fields.SET_NULL, null=True)

    # Features
    features = fields.JSONField(blank=True, null=True)

    # Pricing
    price = fields.DecimalField(max_digits=10, decimal_places=2, null=True, default=0.0)

    # manage_plan
    duration_days = fields.IntField(default=30)
    paused_at = fields.DatetimeField(null=True)
    started_at = fields.DatetimeField(null=True)

    status = fields.CharEnumField(SubscriptionStatus, default=SubscriptionStatus.ACTIVE)
    auto_renewal = fields.BooleanField(default=True)
    current_period_end = fields.DatetimeField(null=True)
    cancel_at_period_end = fields.BooleanField(default=False)

    # Stripe Info
    stripe_customer_id = fields.CharField(max_length=255, null=True)
    stripe_subscription_id = fields.CharField(max_length=255, null=True)
    stripe_price_id = fields.CharField(max_length=255, null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_plans"

    @property
    def expires_at(self):
        if not self.started_at:
            return None
        return self.started_at + timedelta(days=self.duration_days)

    @property
    def is_expired(self):
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) >= self.expires_at

    # Pause Plan
    async def pause_plan(self):
        if self.status != SubscriptionStatus.ACTIVE:
            return
        if self.is_expired:
            return
        now = datetime.now(timezone.utc)
        remaining_seconds = (self.expires_at - now).total_seconds()
        remaining_days = max(int(remaining_seconds // 86400), 0)

        self.duration_days = remaining_days
        self.paused_at = now
        self.status = SubscriptionStatus.PAUSED
        await self.save()


    # Resume Plan
    async def resume_plan(self):
        if self.status != SubscriptionStatus.PAUSED:
            return
        now = datetime.now(timezone.utc)
        self.started_at = now
        self.paused_at = None
        self.status = SubscriptionStatus.ACTIVE
        await self.save()

    def _sync_with_plan(self):
        if not self.plan:
            return

        self.features = self.plan.features

        self.price = self.plan.price
        self.duration_days = self.plan.duration_days

    async def renew(self, at_now: bool = False):
        if not self.plan:
            return
        now = datetime.now(timezone.utc)
        if at_now:
            base_time = now
        # Auto-renew
        elif self.auto_renewal and self.is_expired and self.status == SubscriptionStatus.ACTIVE:
            # extend from previous expiry (not from now)
            base_time = self.expires_at or now
        else:
            return
        self._sync_with_plan()

        # Reset subscription timing
        self.started_at = base_time
        self.paused_at = None
        self.status = SubscriptionStatus.ACTIVE

        await self.save()





class Plan(models.Model):
    id = fields.UUIDField(pk=True)

    # Basic Info
    name = fields.CharField(max_length=50, unique=True)
    description = fields.TextField(null=True)

    # Duration
    duration_days = fields.IntField(default=30)
    features = fields.JSONField(blank=True, null=True)

    # Pricing
    price = fields.DecimalField(max_digits=10, decimal_places=2, null=True, default=0.0)

    is_active = fields.BooleanField(default=True)

    # Stripe Info
    stripe_product_id = fields.CharField(max_length=255, null=True)
    stripe_price_id = fields.CharField(max_length=255, null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "plans"



"""
* ✔ No string-based expiry
* ✔ `is_expired` boolean check
* ✔ Auto-renew only when:
  * `auto_renewal == True`
  * `is_expired == True`
  * `status == ACTIVE`
* ✔ Extends from previous expiry (professional logic)
* ✔ `_sync_with_plan()` clean
* ✔ No incorrect `await`

---

## Current Behavior Summary
### Manual Renew
### Auto Renew (cron/background job)
Works only if:
* Expired
* Auto renewal enabled
* Still ACTIVE

---

Your subscription lifecycle now properly supports:
* Activate
* Pause
* Resume
* Expiry check
* Manual renew
* Auto renew
* Plan feature sync

"""
