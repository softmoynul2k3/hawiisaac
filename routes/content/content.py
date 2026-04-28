from typing import List, Optional

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import get_user_or_none, login_required, permission_required
from app.utils.datetime_formatter import to_utc_z
from applications.content.models import (
    Content,
    ContentBookmark,
    ContentFeedType,
    ContentReaction,
    ContentShare,
    ContentType,
    ContentView,
)
from applications.content.schema import (
    ContentCreate,
    ContentListWithWorkoutsOut,
    ContentOut,
    ContentUpdate,
    normalize_content_text,
    serialize_content,
)
from applications.equipments.models import Workout
from applications.equipments.schema import serialize_workout
from applications.session.models import WorkoutLog, WorkoutSession
from applications.session.schema import StartContentLogOut
from applications.user.models import User


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
    await content.fetch_related("workouts")
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


def _parse_type_filter(content_type: Optional[str]) -> Optional[str]:
    if not content_type:
        return None

    normalized = content_type.strip().lower().replace(" ", "_").replace("-", "_")
    valid_values = {member.value for member in ContentType}
    if normalized in valid_values:
        return normalized

    raise HTTPException(
        status_code=400,
        detail=f"Invalid type filter. Use {', '.join(sorted(valid_values))}.",
    )


async def _can_view_inactive_content(current_user: Optional[User]) -> bool:
    if current_user is None:
        return False
    if current_user.is_superuser:
        return True
    if current_user.is_staff and await current_user.has_permission("view_content"):
        return True
    return False


@router.post(
    "/",
    response_model=ContentOut,
    dependencies=[Depends(permission_required("add_content"))],
)
async def create_content(payload: ContentCreate):
    title = _clean_required_text(payload.title, "Title")
    workout_ids = list(dict.fromkeys(payload.workout_ids))
    workouts = []
    if workout_ids:
        workouts = await Workout.filter(id__in=workout_ids)
        if len(workouts) != len(workout_ids):
            found_ids = {workout.id for workout in workouts}
            missing_ids = [workout_id for workout_id in workout_ids if workout_id not in found_ids]
            raise HTTPException(status_code=404, detail=f"Workout not found for id(s): {', '.join(str(item) for item in missing_ids)}")
    content = await Content.create(
        title=title,
        feed_type=payload.feed_type,
        type=payload.type,
        summary=_clean_optional_text(payload.summary),
        body=_clean_optional_text(payload.body),
        image=_clean_optional_text(payload.image),
        video=_clean_optional_text(payload.video),
        is_active=payload.is_active,
    )
    if workouts:
        workouts_by_id = {workout.id: workout for workout in workouts}
        await content.workouts.add(*[workouts_by_id[workout_id] for workout_id in workout_ids])
    await content.fetch_related("workouts")
    return serialize_content(content)


@router.get("/", response_model=ContentListWithWorkoutsOut)
async def list_contents(
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    feed: Optional[str] = Query(None, description="for_you, browse, expert_tips, or trending"),
    type: Optional[str] = Query(None, description="warmup or forhome"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_user_or_none),
):
    feed_filter = _parse_feed_filter(feed)
    type_filter = _parse_type_filter(type)
    queryset = Content.all()
    workouts = await Workout.all().prefetch_related("category", "equipment", "muscle_groups")
    can_view_inactive = await _can_view_inactive_content(current_user)

    if search:
        cleaned = search.strip()
        queryset = queryset.filter(title__icontains=cleaned)

    if can_view_inactive:
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
    else:
        queryset = queryset.filter(is_active=True)

    if feed_filter and feed_filter != "trending":
        queryset = queryset.filter(feed_type=feed_filter)

    if type_filter:
        queryset = queryset.filter(type=type_filter)

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
        return ContentListWithWorkoutsOut(
            contents=[serialize_content(content) for content in paginated_contents],
            workouts=[await serialize_workout(workout) for workout in workouts],
        )

    contents = await queryset.offset(offset).limit(limit)
    return ContentListWithWorkoutsOut(
        contents=[serialize_content(await _attach_summary(content)) for content in contents],
        workouts=[await serialize_workout(workout) for workout in workouts],
    )


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
    if payload.type is not None:
        content.type = payload.type
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
    if payload.workout_ids is not None:
        workout_ids = list(dict.fromkeys(payload.workout_ids))
        workouts = []
        if workout_ids:
            workouts = await Workout.filter(id__in=workout_ids)
            if len(workouts) != len(workout_ids):
                found_ids = {workout.id for workout in workouts}
                missing_ids = [workout_id for workout_id in workout_ids if workout_id not in found_ids]
                raise HTTPException(status_code=404, detail=f"Workout not found for id(s): {', '.join(str(item) for item in missing_ids)}")
        await content.workouts.clear()
        if workouts:
            workouts_by_id = {workout.id: workout for workout in workouts}
            await content.workouts.add(*[workouts_by_id[workout_id] for workout_id in workout_ids])
    return serialize_content(await _attach_summary(content))


def _serialize_started_workout_log(workout_log: WorkoutLog) -> dict:
    return {
        "id": workout_log.id,
        "workout": {
            "id": workout_log.workout.id,
            "name": workout_log.workout.name,
        },
        "note": workout_log.note,
        "set_logs": [],
        "cardio_log": None,
    }


def _serialize_started_session(session: WorkoutSession, workout_log: WorkoutLog) -> dict:
    return {
        "id": session.id,
        "user_id": session.user_id,
        "date": session.date,
        "duration_minutes": session.duration_minutes,
        "created_at": to_utc_z(session.created_at) or "",
        "workout_logs": [_serialize_started_workout_log(item) for item in session.workout_logs],
    }


@router.post("/{content_id}/start-log", response_model=StartContentLogOut, status_code=status.HTTP_201_CREATED)
async def start_content_log(content_id: int, current_user: User = Depends(login_required)):
    content = await Content.get_or_none(id=content_id).prefetch_related("workouts")
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    linked_workouts = sorted(list(content.workouts), key=lambda item: item.id)
    if not linked_workouts:
        raise HTTPException(status_code=400, detail="This content is not linked to any workouts")

    session = await WorkoutSession.create(
        user=current_user,
        date=date.today(),
        duration_minutes=1,
    )
    created_logs = []
    for workout in linked_workouts:
        workout_log = await WorkoutLog.create(
            session=session,
            workout=workout,
            content=content,
            note=f"Started from content: {content.title}",
        )
        created_logs.append(workout_log)

    await session.fetch_related("workout_logs__workout", "workout_logs__content", "workout_logs__set_logs", "workout_logs__cardio_log")
    first_workout_log = session.workout_logs[0]

    return StartContentLogOut(
        session=_serialize_started_session(session, first_workout_log),
        first_workout_log=_serialize_started_workout_log(first_workout_log),
    )


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
