from enum import Enum

from tortoise import models, fields

class Category(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50)
    description = fields.TextField(null=True, blank=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
    
class Equipment(models.Model):
    id = fields.IntField(pk=True)
    category = fields.ForeignKeyField("models.Category", on_delete=fields.CASCADE, related_name='equipment')
    name = fields.CharField(max_length=50)
    description = fields.TextField(null=True, blank=True)
    image = fields.CharField(max_length=255, blank=True, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class MuscleGroups(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50)
    description = fields.TextField(null=True, blank=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
    

class WorkoutType(str, Enum):
    CARDIO = "cardio"
    NON_CARDIO = "non_cardio"


class Workout(models.Model):
    id = fields.IntField(pk=True)
    category = fields.ForeignKeyField("models.Category", on_delete=fields.CASCADE, related_name='workout')
    equipment = fields.ForeignKeyField("models.Equipment", on_delete=fields.SET_NULL, null=True, related_name='workout')
    muscle_groups = fields.ManyToManyField("models.MuscleGroups", null=True, blank=True)
    name = fields.CharField(max_length=50)
    description = fields.TextField(null=True, blank=True)
    tags = fields.CharField(max_length=255, blank=True, null=True)
    workout_type = fields.CharEnumField(WorkoutType, default=WorkoutType.NON_CARDIO, max_length=20)
    met_value = fields.FloatField(default=5.0)

    sets = fields.CharField(max_length=100)
    reps = fields.CharField(max_length=100)
    rest = fields.CharField(max_length=100)

    time = fields.TimeField(null=True, blank=True)
    distance = fields.IntField(null=True, blank=True)
    speed  = fields.IntField(null=True, blank=True)
    incline  = fields.IntField(null=True, blank=True)

    duration = fields.TimeField(null=True, blank=True)

    uses = fields.JSONField(null=True, blank=True)

    banner = fields.CharField(max_length=255, blank=True, null=True)
    video = fields.CharField(max_length=255, blank=True, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


