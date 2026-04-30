from fastapi import APIRouter, Depends
from tortoise.expressions import Q

from applications.content.models import Content, ContentBookmark
from applications.user.models import User

router = APIRouter()


async def get_current_user() -> User:
    return await User.first()


@router.get("/bookmarks")
async def list_bookmarked_contents(user: User = Depends(get_current_user)):
    bookmarks = await ContentBookmark.filter(user=user).prefetch_related("content")

    contents = [b.content for b in bookmarks if b.content]

    return {
        "count": len(contents),
        "results": [
            {
                "id": c.id,
                "title": c.title,
                "feed_type": c.feed_type,
                "type": c.type,
                "summary": c.summary,
                "image": c.image,
                "video": c.video,
            }
            for c in contents
        ]
    }