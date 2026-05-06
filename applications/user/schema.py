from typing import Dict, Any

from applications.user.models import User, Permission
from applications.user.subscription import SubscriptionStatus



async def serialize_user(user: User) -> Dict[str, Any]:
    await user.fetch_related(
        "groups",
        "groups__permissions",
        "user_permissions",
        "subscription",
        "subscription__plan",
    )


    if user.is_superuser:
        all_codes = await Permission.all().values_list("codename", flat=True)
        permission_codes = {code for code in all_codes if code}
    else:
        permission_codes = {p.codename for p in user.user_permissions if p.codename}
        for group in user.groups:
            for permission in group.permissions:
                if permission.codename:
                    permission_codes.add(permission.codename)


    subscription = getattr(user, "subscription", None)

    is_pro = False
    subscription_data = None

    if (
        subscription
        and subscription.plan
        and subscription.status == SubscriptionStatus.ACTIVE
        and not subscription.is_expired
    ):
        is_pro = subscription.plan.price > 0

        subscription_data = {
            "plan_name": subscription.plan.name,
            "price": float(subscription.plan.price),
            "status": subscription.status,
            "is_expired": subscription.is_expired,
            "expires_at": (
                subscription.expires_at.isoformat()
                if subscription.expires_at
                else None
            ),
        }




    # ---------------- RESPONSE ----------------
    return {
        # -------- BASIC INFO --------
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "auth_provider": user.auth_provider,
        

        # -------- STATUS FLAGS --------
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,

        # -------- PROFILE INFO --------
        "first_name": user.first_name,
        "last_name": user.last_name,
        "bio": user.bio,
        "gender": user.gender,
        "photo": user.photo,
        "dob": user.dob.isoformat() if user.dob else None,

        # -------- SUBSCRIPTION --------
        "is_pro": is_pro,
        "subscription": subscription_data,

        # -------- RELATIONSHIPS --------
        "groups": [{"id": g.id, "name": g.name} for g in user.groups],
        "permissions": [
            {"id": p.id, "codename": p.codename, "name": p.name}
            for p in user.user_permissions
        ],
        "permission_codes": sorted(permission_codes),


        # -------- META --------
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }
