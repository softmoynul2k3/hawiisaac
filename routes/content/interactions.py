from collections import Counter
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.auth import get_user_or_none, login_required
from applications.content.models import Content, ContentBookmark, ContentReaction, ContentShare, ContentView
from applications.content.schema import ContentOut, ContentSummaryOut, serialize_content
from applications.user.models import User


router = APIRouter(prefix="/contents", tags=["Content Interactions"])


class ContentShareCreate(BaseModel):
    platform: Optional[str] = None


class ContentReactionCreate(BaseModel):
    reaction_type: str = "like"


class ReactionSummaryItem(BaseModel):
    reaction_type: str
    count: int


class InteractionStateOut(BaseModel):
    content_id: int
    is_bookmarked: bool
    my_reaction: Optional[str] = None
    bookmark_count: int
    share_count: int
    reaction_count: int
    view_count: int


class ContentEngagementOut(BaseModel):
    content: ContentOut
    reaction_summary: List[ReactionSummaryItem]


async def _get_content_or_404(content_id: int) -> Content:
    content = await Content.get_or_none(id=content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


async def _get_content_summary(content_id: int) -> ContentSummaryOut:
    content = await Content.get_or_none(id=content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    return ContentSummaryOut(
        content_id=content.id,
        bookmark_count=await ContentBookmark.filter(content_id=content_id).count(),
        share_count=await ContentShare.filter(content_id=content_id).count(),
        reaction_count=await ContentReaction.filter(content_id=content_id).count(),
        view_count=await ContentView.filter(content_id=content_id).count(),
    )


async def _get_reaction_summary(content_id: int) -> List[ReactionSummaryItem]:
    reactions = await ContentReaction.filter(content_id=content_id).values_list("reaction_type", flat=True)
    counts = Counter(reactions)
    return [
        ReactionSummaryItem(reaction_type=reaction_type, count=count)
        for reaction_type, count in sorted(counts.items())
    ]


@router.post("/{content_id}/bookmarks", response_model=InteractionStateOut)
async def add_bookmark(content_id: int, current_user: User = Depends(login_required)):
    await _get_content_or_404(content_id)
    await ContentBookmark.get_or_create(user=current_user, content_id=content_id)
    summary = await _get_content_summary(content_id)
    reaction = await ContentReaction.get_or_none(user=current_user, content_id=content_id)
    return InteractionStateOut(
        content_id=content_id,
        is_bookmarked=True,
        my_reaction=reaction.reaction_type if reaction else None,
        bookmark_count=summary.bookmark_count,
        share_count=summary.share_count,
        reaction_count=summary.reaction_count,
        view_count=summary.view_count,
    )


@router.delete("/{content_id}/bookmarks", response_model=InteractionStateOut)
async def remove_bookmark(content_id: int, current_user: User = Depends(login_required)):
    await _get_content_or_404(content_id)
    await ContentBookmark.filter(user=current_user, content_id=content_id).delete()
    summary = await _get_content_summary(content_id)
    reaction = await ContentReaction.get_or_none(user=current_user, content_id=content_id)
    return InteractionStateOut(
        content_id=content_id,
        is_bookmarked=False,
        my_reaction=reaction.reaction_type if reaction else None,
        bookmark_count=summary.bookmark_count,
        share_count=summary.share_count,
        reaction_count=summary.reaction_count,
        view_count=summary.view_count,
    )


@router.post("/{content_id}/shares", response_model=ContentSummaryOut)
async def create_share(content_id: int, payload: ContentShareCreate, current_user: User = Depends(login_required)):
    await _get_content_or_404(content_id)
    platform = (payload.platform or "").strip() or None
    await ContentShare.create(user=current_user, content_id=content_id, platform=platform)
    return await _get_content_summary(content_id)


@router.post("/{content_id}/reactions", response_model=InteractionStateOut)
async def react_content(content_id: int, payload: ContentReactionCreate, current_user: User = Depends(login_required)):
    await _get_content_or_404(content_id)
    reaction_type = (payload.reaction_type or "").strip().lower()
    if not reaction_type:
        raise HTTPException(status_code=400, detail="reaction_type is required")

    reaction = await ContentReaction.get_or_none(user=current_user, content_id=content_id)
    if reaction:
        reaction.reaction_type = reaction_type
        await reaction.save()
    else:
        await ContentReaction.create(user=current_user, content_id=content_id, reaction_type=reaction_type)

    summary = await _get_content_summary(content_id)
    is_bookmarked = await ContentBookmark.filter(user=current_user, content_id=content_id).exists()
    return InteractionStateOut(
        content_id=content_id,
        is_bookmarked=is_bookmarked,
        my_reaction=reaction_type,
        bookmark_count=summary.bookmark_count,
        share_count=summary.share_count,
        reaction_count=summary.reaction_count,
        view_count=summary.view_count,
    )


@router.delete("/{content_id}/reactions", response_model=InteractionStateOut)
async def delete_reaction(content_id: int, current_user: User = Depends(login_required)):
    await _get_content_or_404(content_id)
    await ContentReaction.filter(user=current_user, content_id=content_id).delete()
    summary = await _get_content_summary(content_id)
    is_bookmarked = await ContentBookmark.filter(user=current_user, content_id=content_id).exists()
    return InteractionStateOut(
        content_id=content_id,
        is_bookmarked=is_bookmarked,
        my_reaction=None,
        bookmark_count=summary.bookmark_count,
        share_count=summary.share_count,
        reaction_count=summary.reaction_count,
        view_count=summary.view_count,
    )


@router.post("/{content_id}/views", response_model=ContentSummaryOut)
async def create_view(
    content_id: int,
    request: Request,
    current_user: Optional[User] = Depends(get_user_or_none),
):
    await _get_content_or_404(content_id)
    _ = request
    await ContentView.create(user=current_user, content_id=content_id)
    return await _get_content_summary(content_id)


@router.get("/{content_id}/summary", response_model=ContentEngagementOut)
async def get_content_engagement(content_id: int, current_user: Optional[User] = Depends(get_user_or_none)):
    content = await Content.get_or_none(id=content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    summary = await _get_content_summary(content_id)
    content.bookmark_count = summary.bookmark_count
    content.share_count = summary.share_count
    content.reaction_count = summary.reaction_count
    content.view_count = summary.view_count

    reaction_summary = await _get_reaction_summary(content_id)

    return ContentEngagementOut(
        content=serialize_content(content),
        reaction_summary=reaction_summary,
    )


@router.get("/{content_id}/bookmarks/count", response_model=dict)
async def get_bookmark_count(content_id: int):
    summary = await _get_content_summary(content_id)
    return {"content_id": content_id, "bookmark_count": summary.bookmark_count}


@router.get("/{content_id}/shares/summary", response_model=dict)
async def get_share_summary(content_id: int):
    await _get_content_or_404(content_id)
    shares = await ContentShare.filter(content_id=content_id).values_list("platform", flat=True)
    counts = Counter((platform or "unknown") for platform in shares)
    return {
        "content_id": content_id,
        "share_count": sum(counts.values()),
        "by_platform": [{"platform": platform, "count": count} for platform, count in sorted(counts.items())],
    }


@router.get("/{content_id}/reactions/summary", response_model=dict)
async def get_reaction_summary(content_id: int):
    await _get_content_or_404(content_id)
    summary = await _get_reaction_summary(content_id)
    return {
        "content_id": content_id,
        "reaction_count": sum(item.count for item in summary),
        "items": [item.model_dump() for item in summary],
    }


@router.get("/{content_id}/views/summary", response_model=dict)
async def get_view_summary(content_id: int):
    summary = await _get_content_summary(content_id)
    return {"content_id": content_id, "view_count": summary.view_count}
