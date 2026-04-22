import random
from typing import List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query
from pydantic import BaseModel

from app.auth import permission_required
from app.utils.datetime_formatter import to_utc_z
from applications.equipments.models import Category


router = APIRouter(prefix="/categories", tags=["Categories"])


# ---------------- SERIALIZERS ----------------

class CategoryOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: str


def _normalize_name(name: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Name is required")
    return cleaned


def _serialize_category(category: Category) -> CategoryOut:
    return CategoryOut(
        id=category.id,
        name=category.name,
        description=category.description,
        created_at=to_utc_z(category.created_at) or "",
    )


# ---------------- CREATE ----------------

@router.post(
    "/",
    response_model=CategoryOut,
    dependencies=[Depends(permission_required("add_category"))],
)
async def create_category(
    name: str = Form(...),
    description: Optional[str] = Form(None),
):
    name = _normalize_name(name)

    if await Category.filter(name__iexact=name).exists():
        raise HTTPException(status_code=400, detail="Category already exists")

    category = await Category.create(
        name=name,
        description=description,
    )

    return _serialize_category(category)


# ---------------- LIST ----------------

@router.get("/", response_model=List[CategoryOut])
async def list_categories(
    search: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    queryset = Category.all()

    if search:
        queryset = queryset.filter(name__icontains=search.strip())

    categories = await queryset.offset(offset).limit(limit)

    return [_serialize_category(c) for c in categories]


# ---------------- GET ONE ----------------

@router.get("/{category_id}", response_model=CategoryOut)
async def get_category(category_id: int):
    category = await Category.get_or_none(id=category_id)

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    return _serialize_category(category)


# ---------------- UPDATE ----------------

@router.put(
    "/{category_id}",
    response_model=CategoryOut,
    dependencies=[Depends(permission_required("update_category"))],
)
async def update_category(
    category_id: int,
    name: str = Form(...),
    description: Optional[str] = Form(None),
):
    category = await Category.get_or_none(id=category_id)

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    name = _normalize_name(name)

    if name.lower() != category.name.lower():
        exists = await Category.filter(
            name__iexact=name
        ).exclude(id=category_id).exists()

        if exists:
            raise HTTPException(status_code=400, detail="Name already exists")

        category.name = name

    if description is not None:
        category.description = description

    await category.save()

    return _serialize_category(category)


# ---------------- DELETE ----------------

@router.delete(
    "/{category_id}",
    response_model=dict,
    dependencies=[Depends(permission_required("delete_category"))],
)
async def delete_category(category_id: int):
    category = await Category.get_or_none(id=category_id)

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    await category.delete()

    return {"detail": "Category deleted successfully"}