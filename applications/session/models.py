from tortoise import fields, models


class WorkoutSession(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE, related_name="workout_sessions")
    date = fields.DateField()
    duration_minutes = fields.IntField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"session-{self.id}"


class WorkoutLog(models.Model):
    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField("models.WorkoutSession", on_delete=fields.CASCADE, related_name="workout_logs")
    workout = fields.ForeignKeyField("models.Workout", on_delete=fields.CASCADE, related_name="workout_logs")
    note = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"workout-log-{self.id}"


class SetLog(models.Model):
    id = fields.IntField(pk=True)
    workout_log = fields.ForeignKeyField("models.WorkoutLog", on_delete=fields.CASCADE, related_name="set_logs")
    weight = fields.FloatField()
    reps = fields.IntField()
    order = fields.IntField()
    is_completed = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]
        unique_together = (("workout_log", "order"),)

    def __str__(self):
        return f"set-log-{self.id}"


class CardioLog(models.Model):
    id = fields.IntField(pk=True)
    workout_log = fields.OneToOneField("models.WorkoutLog", on_delete=fields.CASCADE, related_name="cardio_log")
    time_minutes = fields.FloatField()
    distance = fields.FloatField()
    speed = fields.FloatField(null=True)
    incline = fields.FloatField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"cardio-log-{self.id}"
