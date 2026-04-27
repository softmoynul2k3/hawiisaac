from enum import Enum

from tortoise import fields, models


class ContentFeedType(str, Enum):
    FOR_YOU = "for_you"
    BROWSE = "browse"
    EXPERT_TIPS = "expert_tips"


class Content(models.Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=255)
    feed_type = fields.CharEnumField(ContentFeedType, default=ContentFeedType.BROWSE, max_length=20)
    summary = fields.TextField(null=True)
    body = fields.TextField(null=True)
    image = fields.CharField(max_length=255, null=True)
    video = fields.CharField(max_length=255, null=True)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class ContentBookmark(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE, related_name="content_bookmarks")
    content = fields.ForeignKeyField("models.Content", on_delete=fields.CASCADE, related_name="bookmarks")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = (("user", "content"),)


class ContentShare(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE, related_name="content_shares")
    content = fields.ForeignKeyField("models.Content", on_delete=fields.CASCADE, related_name="shares")
    platform = fields.CharField(max_length=50, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ContentReaction(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE, related_name="content_reactions")
    content = fields.ForeignKeyField("models.Content", on_delete=fields.CASCADE, related_name="reactions")
    reaction_type = fields.CharField(max_length=30, default="like")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        unique_together = (("user", "content"),)


class ContentView(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", on_delete=fields.SET_NULL, null=True, related_name="content_views")
    content = fields.ForeignKeyField("models.Content", on_delete=fields.CASCADE, related_name="views")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
