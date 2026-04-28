from typing import Dict, Any

from applications.equipments.models import Category, Equipment, MuscleGroups, Workout


# ---------------- CATEGORY ----------------
async def serialize_category(category: Category) -> Dict[str, Any]:
    return {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "created_at": category.created_at.isoformat() if category.created_at else None,
    }


# ---------------- EQUIPMENT GROUP ----------------
async def serialize_equipment(group: Equipment) -> Dict[str, Any]:
    await group.fetch_related("category")

    return {
        "id": group.id,
        "category": {
            "id": group.category.id,
            "name": group.category.name,
        } if group.category else None,
        "name": group.name,
        "description": group.description,
        "image": group.image,
        "created_at": group.created_at.isoformat() if group.created_at else None,
    }


# ---------------- MUSCLE GROUP ----------------
async def serialize_muscle_group(muscle_group: MuscleGroups) -> Dict[str, Any]:
    return {
        "id": muscle_group.id,
        "name": muscle_group.name,
        "description": muscle_group.description,
        "created_at": muscle_group.created_at.isoformat() if muscle_group.created_at else None,
    }


# ---------------- EQUIPMENT ----------------
async def serialize_workout(equipment: Workout) -> Dict[str, Any]:
    await equipment.fetch_related("category", "equipment", "muscle_groups")

    return {
        "id": equipment.id,
        "name": equipment.name,
        "description": equipment.description,
        "category": {
            "id": equipment.category.id,
            "name": equipment.category.name,
        } if equipment.category else None,
        "equipment": {
            "id": equipment.equipment.id,
            "name": equipment.equipment.name,
        } if equipment.equipment else None,
        "muscle_groups": [
            {
                "id": muscle_group.id,
                "name": muscle_group.name,
                "description": muscle_group.description,
            }
            for muscle_group in equipment.muscle_groups
        ],
        "tags": equipment.tags,
        "workout_type": equipment.workout_type,
        "met_value": equipment.met_value,
        "sets": equipment.sets,
        "reps": equipment.reps,
        "rest": equipment.rest,
        "uses": equipment.uses,
        "banner": equipment.banner,
        "video": equipment.video,
        "created_at": equipment.created_at.isoformat() if equipment.created_at else None,
    }
