from enum import Enum

from tortoise import fields, models


class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"


class WorkoutSession(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE, related_name="workout_sessions")
    date = fields.DateField()
    duration_minutes = fields.IntField(default=0)
    note = fields.TextField(null=True)
    user_weight_kg = fields.FloatField(null=True)
    status = fields.CharEnumField(SessionStatus, default=SessionStatus.ACTIVE, max_length=20)
    current_workout_order = fields.IntField(default=1)
    completed_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"session-{self.id}"


class SessionWorkout(models.Model):
    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField("models.WorkoutSession", on_delete=fields.CASCADE, related_name="workouts")
    workout = fields.ForeignKeyField("models.Workout", on_delete=fields.CASCADE, related_name="session_workouts")
    content = fields.ForeignKeyField("models.Content", on_delete=fields.SET_NULL, null=True, related_name="session_workouts")
    order = fields.IntField()
    note = fields.TextField(null=True)
    is_completed = fields.BooleanField(default=False)
    estimated_calories_burned = fields.FloatField(default=0)
    actual_calories_burned = fields.FloatField(default=0)
    completed_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]
        unique_together = (("session", "order"),)

    def __str__(self):
        return f"session-workout-{self.id}"


class SetLog(models.Model):
    id = fields.IntField(pk=True)
    session_workout = fields.ForeignKeyField("models.SessionWorkout", on_delete=fields.CASCADE, related_name="set_logs")
    weight = fields.FloatField()
    reps = fields.IntField()
    order = fields.IntField()
    duration_seconds = fields.IntField(default=0)
    is_completed = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]
        unique_together = (("session_workout", "order"),)

    def __str__(self):
        return f"set-log-{self.id}"


class CardioLog(models.Model):
    id = fields.IntField(pk=True)
    session_workout = fields.OneToOneField("models.SessionWorkout", on_delete=fields.CASCADE, related_name="cardio_log")
    time_minutes = fields.FloatField()
    distance = fields.FloatField()
    speed = fields.FloatField(null=True)
    incline = fields.FloatField(null=True)
    calories_burned = fields.FloatField(default=0)
    user_weight_kg = fields.FloatField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"cardio-log-{self.id}"
