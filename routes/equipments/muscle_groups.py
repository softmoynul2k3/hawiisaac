from typing import List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query
from pydantic import BaseModel

from app.auth import permission_required
from app.utils.datetime_formatter import to_utc_z
from applications.equipments.models import MuscleGroups


router = APIRouter(prefix="/muscle-groups", tags=["MuscleGroups"])


# ---------------- SERIALIZER ----------------

class MuscleGroupOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: str


def _normalize_name(name: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Name is required")
    return cleaned


def _serialize_muscle_group(muscle_group: MuscleGroups) -> MuscleGroupOut:
    return MuscleGroupOut(
        id=muscle_group.id,
        name=muscle_group.name,
        description=muscle_group.description,
        created_at=to_utc_z(muscle_group.created_at) or "",
    )


# ---------------- CREATE ----------------

@router.post(
    "/",
    response_model=MuscleGroupOut,
    dependencies=[Depends(permission_required("add_muscle_group"))],
)
async def create_muscle_group(
    name: str = Form(...),
    description: Optional[str] = Form(None),
):
    name = _normalize_name(name)

    if await MuscleGroups.filter(name__iexact=name).exists():
        raise HTTPException(status_code=400, detail="Muscle group already exists")

    muscle_group = await MuscleGroups.create(
        name=name,
        description=description,
    )

    return _serialize_muscle_group(muscle_group)


# ---------------- LIST ----------------
@router.get("/", response_model=List[MuscleGroupOut])
async def list_muscle_groups(
    search: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    queryset = MuscleGroups.all()

    if search:
        queryset = queryset.filter(name__icontains=search.strip())

    muscle_groups = await queryset.offset(offset).limit(limit)

    return [_serialize_muscle_group(g) for g in muscle_groups]


# ---------------- GET ----------------

@router.get("/{muscle_group_id}", response_model=MuscleGroupOut)
async def get_muscle_group(muscle_group_id: int):
    muscle_group = await MuscleGroups.get_or_none(id=muscle_group_id)

    if not muscle_group:
        raise HTTPException(status_code=404, detail="Muscle group not found")

    return _serialize_muscle_group(muscle_group)


# ---------------- UPDATE ----------------

@router.put(
    "/{muscle_group_id}",
    response_model=MuscleGroupOut,
    dependencies=[Depends(permission_required("update_muscle_group"))],
)
async def update_muscle_group(
    muscle_group_id: int,
    name: str = Form(...),
    description: Optional[str] = Form(None),
):
    muscle_group = await MuscleGroups.get_or_none(id=muscle_group_id)

    if not muscle_group:
        raise HTTPException(status_code=404, detail="Muscle group not found")

    name = _normalize_name(name)

    if name.lower() != muscle_group.name.lower():
        exists = await MuscleGroups.filter(
            name__iexact=name
        ).exclude(id=muscle_group_id).exists()

        if exists:
            raise HTTPException(status_code=400, detail="Muscle group name already exists")

        muscle_group.name = name

    if description is not None:
        muscle_group.description = description

    await muscle_group.save()

    return _serialize_muscle_group(muscle_group)


# ---------------- DELETE ----------------

@router.delete(
    "/{muscle_group_id}",
    response_model=dict,
    dependencies=[Depends(permission_required("delete_muscle_group"))],
)
async def delete_muscle_group(muscle_group_id: int):
    muscle_group = await MuscleGroups.get_or_none(id=muscle_group_id)

    if not muscle_group:
        raise HTTPException(status_code=404, detail="Muscle group not found")

    await muscle_group.delete()

    return {"detail": "Muscle group deleted successfully"}
