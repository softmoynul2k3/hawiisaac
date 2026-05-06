from typing import List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.auth import permission_required
from app.utils.datetime_formatter import to_utc_z
from applications.equipments.models import Category, Equipment
from app.utils.file_manager import delete_file, save_file, update_file


router = APIRouter(prefix="/equipments", tags=["Equipment"])


# ---------------- SERIALIZER ----------------

class EquipmentOut(BaseModel):
    id: int
    category: Optional[dict] = None
    name: str
    description: Optional[str] = None
    image: Optional[str] = None
    is_free: Optional[bool] = None
    created_at: str


def _normalize_name(name: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Name is required")
    return cleaned


def _serialize_equipment(equipment: Equipment) -> EquipmentOut:
    return EquipmentOut(
        id=equipment.id,
        category={
            "id": equipment.category.id,
            "name": equipment.category.name,
        } if getattr(equipment, "category", None) else None,
        name=equipment.name,
        description=equipment.description,
        image=equipment.image,
        is_free=equipment.is_free,
        created_at=to_utc_z(equipment.created_at) or "",
    )


# ---------------- CREATE ----------------

@router.post(
    "/",
    response_model=EquipmentOut,
    dependencies=[Depends(permission_required("add_equipment"))],
)
async def create_equipment(
    category_id: int = Form(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    is_free: Optional[bool] = Form(None),
    image: Optional[UploadFile] = None,
):
    category = await Category.get_or_none(id=category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    name = _normalize_name(name)

    if await Equipment.filter(name__iexact=name, category_id=category_id).exists():
        raise HTTPException(status_code=400, detail="Equipment already exists")

    image_url = None
    if image and image.filename:
        image_url = await save_file(image, upload_to="equipments")

    equipment = await Equipment.create(
        category=category,
        name=name,
        description=description,
        image=image_url,
        is_free=is_free,
    )

    await equipment.fetch_related("category")
    return _serialize_equipment(equipment)


# ---------------- LIST ----------------
@router.get("/", response_model=List[EquipmentOut])
async def list_equipments(
    search: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    is_free: Optional[bool] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    queryset = Equipment.all().prefetch_related("category")

    if search:
        queryset = queryset.filter(name__icontains=search.strip())

    if is_free is not None:
        queryset = queryset.filter(is_free=is_free)

    if category_id is not None:
        queryset = queryset.filter(category_id=category_id)

    equipments = await queryset.offset(offset).limit(limit)

    return [_serialize_equipment(g) for g in equipments]


# ---------------- GET ----------------

@router.get("/{equipment_id}", response_model=EquipmentOut)
async def get_equipment(equipment_id: int):
    equipment = await Equipment.get_or_none(id=equipment_id).prefetch_related("category")

    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    return _serialize_equipment(equipment)


# ---------------- UPDATE ----------------

@router.put(
    "/{equipment_id}",
    response_model=EquipmentOut,
    dependencies=[Depends(permission_required("update_equipment"))],
)
async def update_equipment(
    equipment_id: int,
    category_id: Optional[int] = Form(None),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    is_free: Optional[bool] = Form(None),
    image: Optional[UploadFile] = None,
):
    equipment = await Equipment.get_or_none(id=equipment_id).prefetch_related("category")

    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    current_category_id = equipment.category_id

    if category_id is not None:
        category = await Category.get_or_none(id=category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        equipment.category = category

    name = _normalize_name(name)

    target_category_id = category_id if category_id is not None else current_category_id

    if name.lower() != equipment.name.lower() or target_category_id != current_category_id:
        exists = await Equipment.filter(
            name__iexact=name,
            category_id=target_category_id,
        ).exclude(id=equipment_id).exists()

        if exists:
            raise HTTPException(status_code=400, detail="Equipment already exists in this category")

        equipment.name = name

    if description is not None:
        equipment.description = description

    if image and image.filename:
        equipment.image = await update_file(
            image,
            file_url=equipment.image,
            upload_to="equipments",
        )
    if is_free is not None:
        equipment.is_free = is_free

    await equipment.save()

    await equipment.fetch_related("category")
    return _serialize_equipment(equipment)


# ---------------- DELETE ----------------

@router.delete(
    "/{equipment_id}",
    response_model=dict,
    dependencies=[Depends(permission_required("delete_equipment"))],
)
async def delete_equipment(equipment_id: int):
    equipment = await Equipment.get_or_none(id=equipment_id)

    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    if equipment.image:
        await delete_file(equipment.image)

    await equipment.delete()

    return {"detail": "Equipment deleted successfully"}
