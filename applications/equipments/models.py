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
    
class Workout(models.Model):
    id = fields.IntField(pk=True)
    category = fields.ForeignKeyField("models.Category", on_delete=fields.CASCADE, related_name='workout')
    equipment = fields.ForeignKeyField("models.Equipment", on_delete=fields.SET_NULL, null=True, related_name='workout')
    muscle_groups = fields.ManyToManyField("models.MuscleGroups", null=True, blank=True)
    name = fields.CharField(max_length=50)
    description = fields.TextField(null=True, blank=True)
    tags = fields.CharField(max_length=255, blank=True, null=True)

    sets = fields.CharField(max_length=100)
    reps = fields.CharField(max_length=100)
    rest = fields.CharField(max_length=100)
    uses = fields.JSONField(null=True, blank=True)

    banner = fields.CharField(max_length=255, blank=True, null=True)
    video = fields.CharField(max_length=255, blank=True, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


