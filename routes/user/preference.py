from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException
from app.auth import login_required
from applications.user.models import DistanceChoice, MeasurementChoice, Preference, User, WeightChoice


router = APIRouter(prefix="/preference", tags=['Preference'])

@router.post("/")
async def create_preference(
    weight: Optional[WeightChoice] = Form(WeightChoice.KG),
    distance: Optional[DistanceChoice] = Form(DistanceChoice.KM),
    measurements: Optional[MeasurementChoice] = Form(MeasurementChoice.CM),
    user: User = Depends(login_required),
):
    pref = await Preference.get_or_none(user=user)

    if pref:
        pref.weight = weight
        pref.distance = distance
        pref.measurements = measurements
        await pref.save()
    else:
        pref = await Preference.create(
            user=user,
            weight=weight,
            distance=distance,
            measurements=measurements,
        )

    return pref


# ✅ Read
@router.get("/")
async def get_preference(user: User = Depends(login_required)):
    pref = await Preference.get_or_none(user=user)
    if not pref:
        pref = await Preference.create(user=user)
    return pref


# ✅ Update (partial)
@router.put("/")
async def update_preference(
    weight: Optional[WeightChoice] = Form(None),
    distance: Optional[DistanceChoice] = Form(None),
    measurements: Optional[MeasurementChoice] = Form(None),
    user: User = Depends(login_required),
):
    pref = await Preference.get_or_none(user=user)
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")

    if weight is not None:
        pref.weight = weight
    if distance is not None:
        pref.distance = distance
    if measurements is not None:
        pref.measurements = measurements

    await pref.save()
    return pref


# ✅ Delete
@router.delete("/")
async def delete_preference(user: User = Depends(login_required)):
    pref = await Preference.get_or_none(user=user)
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")

    await pref.delete()
    return {"detail": "Preference deleted"}