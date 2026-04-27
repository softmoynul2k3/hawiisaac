from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import permission_required
from applications.content.models import (
    Content,
    ContentBookmark,
    ContentFeedType,
    ContentReaction,
    ContentShare,
    ContentView,
)
from applications.content.schema import (
    ContentCreate,
    ContentOut,
    ContentUpdate,
    normalize_content_text,
    serialize_content,
)


router = APIRouter(prefix="/contents", tags=["Content"])


def _clean_required_text(value: str, field_name: str) -> str:
    try:
        return normalize_content_text(value, required=True, field_name=field_name) or ""
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _clean_optional_text(value: Optional[str]) -> Optional[str]:
    try:
        return normalize_content_text(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def _attach_summary(content: Content) -> Content:
    content.bookmark_count = await ContentBookmark.filter(content_id=content.id).count()
    content.share_count = await ContentShare.filter(content_id=content.id).count()
    content.reaction_count = await ContentReaction.filter(content_id=content.id).count()
    content.view_count = await ContentView.filter(content_id=content.id).count()
    return content


def _parse_feed_filter(feed: Optional[str]) -> Optional[str]:
    if not feed:
        return None

    normalized = feed.strip().lower().replace(" ", "_").replace("-", "_")
    valid_values = {member.value for member in ContentFeedType}
    if normalized == "trending" or normalized in valid_values:
        return normalized

    raise HTTPException(
        status_code=400,
        detail="Invalid feed filter. Use for_you, browse, expert_tips, or trending.",
    )


@router.post(
    "/",
    response_model=ContentOut,
    dependencies=[Depends(permission_required("add_content"))],
)
async def create_content(payload: ContentCreate):
    title = _clean_required_text(payload.title, "Title")
    content = await Content.create(
        title=title,
        feed_type=payload.feed_type,
        summary=_clean_optional_text(payload.summary),
        body=_clean_optional_text(payload.body),
        image=_clean_optional_text(payload.image),
        video=_clean_optional_text(payload.video),
        is_active=payload.is_active,
    )
    return serialize_content(content)


@router.get("/", response_model=List[ContentOut])
async def list_contents(
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    feed: Optional[str] = Query(None, description="for_you, browse, expert_tips, or trending"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    feed_filter = _parse_feed_filter(feed)
    queryset = Content.all()

    if search:
        cleaned = search.strip()
        queryset = queryset.filter(title__icontains=cleaned)

    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)

    if feed_filter and feed_filter != "trending":
        queryset = queryset.filter(feed_type=feed_filter)

    if feed_filter == "trending":
        contents = [await _attach_summary(content) for content in await queryset]
        ranked_contents = sorted(
            contents,
            key=lambda content: (
                content.view_count,
                content.reaction_count,
                content.share_count,
                content.bookmark_count,
                content.created_at,
            ),
            reverse=True,
        )
        paginated_contents = ranked_contents[offset:offset + limit]
        return [serialize_content(content) for content in paginated_contents]

    contents = await queryset.offset(offset).limit(limit)
    return [serialize_content(await _attach_summary(content)) for content in contents]


@router.get("/{content_id}", response_model=ContentOut)
async def get_content(content_id: int):
    content = await Content.get_or_none(id=content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return serialize_content(await _attach_summary(content))


@router.put(
    "/{content_id}",
    response_model=ContentOut,
    dependencies=[Depends(permission_required("update_content"))],
)
async def update_content(content_id: int, payload: ContentUpdate):
    content = await Content.get_or_none(id=content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    if payload.title is not None:
        content.title = _clean_required_text(payload.title, "Title")
    if payload.feed_type is not None:
        content.feed_type = payload.feed_type
    if payload.summary is not None:
        content.summary = _clean_optional_text(payload.summary)
    if payload.body is not None:
        content.body = _clean_optional_text(payload.body)
    if payload.image is not None:
        content.image = _clean_optional_text(payload.image)
    if payload.video is not None:
        content.video = _clean_optional_text(payload.video)
    if payload.is_active is not None:
        content.is_active = payload.is_active

    await content.save()
    return serialize_content(await _attach_summary(content))


@router.delete(
    "/{content_id}",
    response_model=dict,
    dependencies=[Depends(permission_required("delete_content"))],
)
async def delete_content(content_id: int):
    content = await Content.get_or_none(id=content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    await content.delete()
    return {"detail": "Content deleted successfully"}
