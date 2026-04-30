from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from datetime import timedelta, time
from app.utils.datetime_formatter import to_utc_z
from applications.content.models import Content, ContentFeedType, ContentType


class ContentCreate(BaseModel):
    title: str
    feed_type: ContentFeedType = ContentFeedType.BROWSE
    type: ContentType = ContentType.WARMUP
    workout_ids: list[int] = []
    summary: Optional[str] = None
    body: Optional[str] = None
    image: Optional[str] = None
    video: Optional[str] = None
    is_active: bool = True


class ContentUpdate(BaseModel):
    title: Optional[str] = None
    feed_type: Optional[ContentFeedType] = None
    type: Optional[ContentType] = None
    workout_ids: Optional[list[int]] = None
    summary: Optional[str] = None
    body: Optional[str] = None
    image: Optional[str] = None
    video: Optional[str] = None
    is_active: Optional[bool] = None


class ContentOut(BaseModel):
    id: int
    title: str
    feed_type: ContentFeedType
    type: ContentType
    workouts: list[dict] = []
    summary: Optional[str] = None
    body: Optional[str] = None
    image: Optional[str] = None
    video: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str
    bookmark_count: int = 0
    share_count: int = 0
    reaction_count: int = 0
    view_count: int = 0


class ContentListItemOut(BaseModel):
    id: int
    title: str
    feed_type: ContentFeedType
    type: ContentType
    summary: Optional[str] = None
    body: Optional[str] = None
    image: Optional[str] = None
    video: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str
    bookmark_count: int = 0
    share_count: int = 0
    reaction_count: int = 0
    view_count: int = 0


class ContentSummaryOut(BaseModel):
    content_id: int
    bookmark_count: int
    share_count: int
    reaction_count: int
    view_count: int


class ContentListWithWorkoutsOut(BaseModel):
    contents: list[ContentListItemOut]
    workouts: list[dict]


def normalize_content_text(value: Optional[str], *, required: bool = False, field_name: str = "Value") -> Optional[str]:
    if value is None:
        if required:
            raise ValueError(f"{field_name} is required")
        return None

    cleaned = value.strip()
    if required and not cleaned:
        raise ValueError(f"{field_name} is required")
    return cleaned or None


def timedelta_to_str(value) -> str | None:
    """Convert timedelta or time to HH:MM:SS string."""

    if value is None:
        return None

    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    if isinstance(value, time):
        return value.isoformat()

    return str(value)

def serialize_content(content: Content) -> ContentOut:
    workouts = sorted(list(getattr(content, "workouts", []) or []), key=lambda item: item.id)
    return ContentOut(
        id=content.id,
        title=content.title,
        feed_type=content.feed_type,
        type=content.type,
        workouts=[
            {
                "id": workout.id,
                "name": workout.name,
                "workout_type": workout.workout_type,
                "met_value": workout.met_value,
                "time": timedelta_to_str(workout.time),
                "duration": timedelta_to_str(workout.duration),
                "distance": workout.distance,
                "speed": workout.speed,
                "incline": workout.incline,
            }
            for workout in workouts
        ],
        summary=content.summary,
        body=content.body,
        image=content.image,
        video=content.video,
        is_active=content.is_active,
        created_at=to_utc_z(content.created_at) or "",
        updated_at=to_utc_z(content.updated_at) or "",
        bookmark_count=getattr(content, "bookmark_count", 0) or 0,
        share_count=getattr(content, "share_count", 0) or 0,
        reaction_count=getattr(content, "reaction_count", 0) or 0,
        view_count=getattr(content, "view_count", 0) or 0,
    )


def serialize_content_list_item(content: Content) -> ContentListItemOut:
    return ContentListItemOut(
        id=content.id,
        title=content.title,
        feed_type=content.feed_type,
        type=content.type,
        summary=content.summary,
        body=content.body,
        image=content.image,
        video=content.video,
        is_active=content.is_active,
        created_at=to_utc_z(content.created_at) or "",
        updated_at=to_utc_z(content.updated_at) or "",
        bookmark_count=getattr(content, "bookmark_count", 0) or 0,
        share_count=getattr(content, "share_count", 0) or 0,
        reaction_count=getattr(content, "reaction_count", 0) or 0,
        view_count=getattr(content, "view_count", 0) or 0,
    )
