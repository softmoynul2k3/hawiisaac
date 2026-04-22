from enum import Enum

from passlib.context import CryptContext
from tortoise import fields, models

pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")


class Permission(models.Model):
    id = fields.IntField(pk=True, readonly=True, hidden=True)
    name = fields.CharField(max_length=100, unique=True, editable=False)
    codename = fields.CharField(max_length=100, unique=True, editable=False)

    def __str__(self):
        return self.codename


class Group(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, unique=True)

    permissions: fields.ManyToManyRelation["Permission"] = fields.ManyToManyField(
        "models.Permission",
        related_name="groups",
        through="group_permissions",
    )

    def __str__(self):
        return self.name


class User(models.Model):
    id = fields.UUIDField(pk=True, editable=False, hidden=True)
    username = fields.CharField(max_length=120, null=True, unique=True)
    email = fields.CharField(max_length=120, null=True, unique=True)
    password = fields.CharField(max_length=2000, default="")
    first_name = fields.CharField(max_length=100, null=True)
    last_name = fields.CharField(max_length=100, null=True)
    gender = fields.CharField(max_length=20, null=True)
    dob = fields.DateField(null=True)
    photo = fields.CharField(max_length=400, null=True)
    google_id = fields.CharField(max_length=255, null=True, unique=True)
    apple_id = fields.CharField(max_length=255, null=True, unique=True)
    auth_provider = fields.CharField(max_length=20, null=True)

    is_active_2fa = fields.BooleanField(default=False)

    is_active = fields.BooleanField(default=True)
    is_superuser = fields.BooleanField(default=False)
    is_staff= fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    groups: fields.ManyToManyRelation["Group"] = fields.ManyToManyField(
        "models.Group",
        related_name="users",
        through="user_groups",
    )
    user_permissions: fields.ManyToManyRelation["Permission"] = fields.ManyToManyField(
        "models.Permission",
        related_name="users",
        through="user_permissions",
    )

    class Meta:
        table = "users"

    @classmethod
    def set_password(cls, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        if not self.password:
            return False
        try:
            return pwd_context.verify(password, self.password)
        except Exception:
            return False

    def __str__(self):
        display = f"user-{self.username}" or self.email or  str(self.id)
        return f"{display}"

    async def has_permission(self, codename: str) -> bool:
        if self.is_superuser:
            return True

        await self.fetch_related("user_permissions", "groups__permissions")

        for perm in self.user_permissions:
            if perm.codename == codename:
                return True

        for group in self.groups:
            for perm in group.permissions:
                if perm.codename == codename:
                    return True
        return False

    async def save(self, *args, **kwargs):
        await super().save(*args, **kwargs)



class WeightChoice(str, Enum):
    KG = "kg"
    LBS = "lbs"


class DistanceChoice(str, Enum):
    KM = "km"
    MILE = "mile"


class MeasurementChoice(str, Enum):
    CM = "cm"
    INCH = "inch"


class Preference(models.Model):
    id = fields.IntField(pk=True)
    user = fields.OneToOneField("models.User", on_delete=fields.CASCADE, related_name="preference")

    weight = fields.CharEnumField(WeightChoice, default=WeightChoice.KG, max_length=5)
    distance = fields.CharEnumField(DistanceChoice, default=DistanceChoice.KM, max_length=10)
    measurements = fields.CharEnumField(MeasurementChoice, default=MeasurementChoice.CM, max_length=10)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
