from typing import List, Optional
import json

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile
from tortoise.expressions import Q

from app.auth import permission_required
from app.utils.file_manager import save_file, update_file, delete_file

from applications.equipments.models import Workout, Category, Equipment, MuscleGroups
from applications.equipments.schema import serialize_workout


router = APIRouter(prefix="/workout", tags=["Workout"])


def _parse_uses(uses: Optional[str]):
    if uses is None:
        return None
    if not uses.strip():
        return []

    try:
        parsed = json.loads(uses)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid uses JSON") from exc

    if not isinstance(parsed, list):
        raise HTTPException(status_code=400, detail="Uses must be a JSON array")

    return parsed


def _normalize_required_text(value: str, field_name: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail=f"{field_name} is required")
    return cleaned


def _normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


async def _parse_muscle_group_ids(muscle_group_ids: Optional[str]) -> Optional[List[MuscleGroups]]:
    if muscle_group_ids is None:
        return None
    if not muscle_group_ids.strip():
        return []

    try:
        parsed = json.loads(muscle_group_ids)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid muscle_group_ids JSON") from exc

    if not isinstance(parsed, list) or not all(isinstance(item, int) for item in parsed):
        raise HTTPException(status_code=400, detail="muscle_group_ids must be a JSON array of integers")

    unique_ids = list(dict.fromkeys(parsed))
    muscle_groups = await MuscleGroups.filter(id__in=unique_ids)

    if len(muscle_groups) != len(unique_ids):
        found_ids = {muscle_group.id for muscle_group in muscle_groups}
        missing_ids = [item for item in unique_ids if item not in found_ids]
        raise HTTPException(
            status_code=404,
            detail=f"Muscle group not found for id(s): {', '.join(str(item) for item in missing_ids)}",
        )

    muscle_groups_by_id = {muscle_group.id: muscle_group for muscle_group in muscle_groups}
    return [muscle_groups_by_id[item] for item in unique_ids]


# ---------------- CREATE ----------------

@router.post(
    "/",
    response_model=dict,
    dependencies=[Depends(permission_required("add_workout"))],
)
async def create_workout(
    category_id: int = Form(...),
    equipment_id: Optional[int] = Form(None),
    muscle_group_ids: Optional[str] = Form(None),
    name: str = Form(...),
    description: Optional[str] = Form(None),

    sets: str = Form(...),
    reps: str = Form(...),
    rest: str = Form(...),
    uses: Optional[str] = Form(None),

    tags: Optional[str] = Form(None, description="use comma for seperate."),
    banner: Optional[UploadFile] = None,
    video: Optional[UploadFile] = None,
):
    category = await Category.get_or_none(id=category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    equipment = None
    if equipment_id is not None:
        equipment = await Equipment.get_or_none(id=equipment_id)
        if not equipment:
            raise HTTPException(status_code=404, detail="Equipment not found")

    muscle_groups = await _parse_muscle_group_ids(muscle_group_ids)
    name = _normalize_required_text(name, "Name")
    banner_url = await save_file(banner, upload_to="workouts/banner") if banner and banner.filename else None
    video_url = await save_file(video, upload_to="workouts/video", compress=False) if video and video.filename else None

    workout = await Workout.create(
        category=category,
        equipment=equipment,
        name=name,
        description=_normalize_optional_text(description),
        tags=_normalize_optional_text(tags),
        sets=_normalize_required_text(sets, "Sets"),
        reps=_normalize_required_text(reps, "Reps"),
        rest=_normalize_required_text(rest, "Rest"),
        uses=_parse_uses(uses),
        banner=banner_url,
        video=video_url,
    )

    if muscle_groups is not None:
        await workout.muscle_groups.clear()
        if muscle_groups:
            await workout.muscle_groups.add(*muscle_groups)

    return await serialize_workout(workout)


# ---------------- LIST ----------------

@router.get("/", response_model=List[dict])
async def list_workout(
    search: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    equipment_id: Optional[int] = Query(None),
    muscle_group_id: Optional[int] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    queryset = Workout.all().prefetch_related("category", "equipment", "muscle_groups")

    if search:
        search = search.strip()

        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )


    if category_id:
        queryset = queryset.filter(category_id=category_id)

    if equipment_id:
        queryset = queryset.filter(equipment_id=equipment_id)

    if muscle_group_id:
        queryset = queryset.filter(muscle_groups__id=muscle_group_id)

    workouts = await queryset.distinct().offset(offset).limit(limit)

    return [await serialize_workout(workout) for workout in workouts]


# ---------------- GET ONE ----------------

@router.get("/{workout_id}", response_model=dict)
async def get_workout(workout_id: int):
    workout = await Workout.get_or_none(id=workout_id).prefetch_related(
        "category", "equipment", "muscle_groups"
    )

    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    return await serialize_workout(workout)


# ---------------- UPDATE ----------------

@router.put(
    "/{workout_id}",
    response_model=dict,
    dependencies=[Depends(permission_required("update_workout"))],
)
async def update_workout(
    workout_id: int,

    category_id: Optional[int] = Form(None),
    equipment_id: Optional[int] = Form(None),
    muscle_group_ids: Optional[str] = Form(None),

    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),

    sets: Optional[str] = Form(None),
    reps: Optional[str] = Form(None),
    rest: Optional[str] = Form(None),
    uses: Optional[str] = Form(None),

    tags: Optional[str] = Form(None),
    banner: Optional[UploadFile] = None,
    video: Optional[UploadFile] = None,
):
    workout = await Workout.get_or_none(id=workout_id)

    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    # -------- RELATIONS --------
    if category_id is not None:
        category = await Category.get_or_none(id=category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        workout.category = category

    if equipment_id is not None:
        if equipment_id == 0:
            workout.equipment = None
        else:
            equipment = await Equipment.get_or_none(id=equipment_id)
            if not equipment:
                raise HTTPException(status_code=404, detail="Equipment not found")
            workout.equipment = equipment

    muscle_groups = await _parse_muscle_group_ids(muscle_group_ids)

    # -------- FIELDS --------
    if name is not None:
        workout.name = _normalize_required_text(name, "Name")

    if description is not None:
        workout.description = _normalize_optional_text(description)

    if sets is not None:
        workout.sets = _normalize_required_text(sets, "Sets")

    if reps is not None:
        workout.reps = _normalize_required_text(reps, "Reps")

    if rest is not None:
        workout.rest = _normalize_required_text(rest, "Rest")

    if uses is not None:
        workout.uses = _parse_uses(uses)

    if tags is not None:
        workout.tags = _normalize_optional_text(tags)

    if banner and banner.filename:
        workout.banner = await update_file(
            banner,
            file_url=workout.banner,
            upload_to="workouts/banner",
        )

    if video and video.filename:
        workout.video = await update_file(
            video,
            file_url=workout.video,
            upload_to="workouts/video",
            compress=False,
        )

    await workout.save()

    if muscle_groups is not None:
        await workout.muscle_groups.clear()
        if muscle_groups:
            await workout.muscle_groups.add(*muscle_groups)

    await workout.fetch_related("category", "equipment", "muscle_groups")

    return await serialize_workout(workout)


# ---------------- DELETE ----------------

@router.delete(
    "/{workout_id}",
    response_model=dict,
    dependencies=[Depends(permission_required("delete_workout"))],
)
async def delete_workout(workout_id: int):
    workout = await Workout.get_or_none(id=workout_id)

    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    if workout.banner:
        await delete_file(workout.banner)

    if workout.video:
        await delete_file(workout.video)

    await workout.delete()

    return {"detail": "Workout deleted successfully"}
