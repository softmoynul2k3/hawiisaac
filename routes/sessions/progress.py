# from collections import defaultdict
# from datetime import datetime, timezone
# from typing import List, Optional
# from uuid import UUID
# from datetime import date

# from fastapi import APIRouter, Depends, HTTPException, Query
# from tortoise.functions import Avg

# from app.auth import login_required
# from applications.session.models import SessionWorkout, SetLog, WorkoutSession
# from applications.session.schema import (
#     ProgressBestOut,
#     ProgressChartPoint,
#     ProgressSummaryOut,
# )
# from applications.user.models import User


# router = APIRouter(tags=["Progress"])


# async def _allowed_session_access(current_user: User, target_user: User, action: str) -> bool:
#     is_self = current_user.id == target_user.id

#     if action == "view":
#         if is_self:
#             return True
#         return current_user.is_superuser or await current_user.has_permission("view_user")

#     if action == "manage":
#         if is_self:
#             return True
#         return current_user.is_superuser or await current_user.has_permission("update_user")

#     return False

# async def _resolve_target_user(current_user: User, user_id: Optional[UUID], action: str) -> User:
#     if user_id is None:
#         return current_user

#     target_user = await User.get_or_none(id=user_id)
#     if not target_user:
#         raise HTTPException(status_code=404, detail="User not found")

#     if not await _allowed_session_access(current_user, target_user, action):
#         raise HTTPException(status_code=403, detail="Permission denied.")

#     return target_user

# def _one_rm(weight: float, reps: int) -> float:
#     return round(weight * (1 + (reps / 30)), 2)


# def _apply_date_filter(query, start_date: Optional[date], end_date: Optional[date]):
#     if start_date:
#         query = query.filter(session__date__gte=start_date)
#     if end_date:
#         query = query.filter(session__date__lte=end_date)
#     return query



# @router.get("/progress/summary", response_model=ProgressSummaryOut)
# async def progress_summary(
#     user_id: Optional[UUID] = Query(None),
#     start_date: Optional[date] = Query(None),
#     end_date: Optional[date] = Query(None),
#     current_user: User = Depends(login_required),
# ):
#     target_user = await _resolve_target_user(current_user, user_id, "view")

#     total_workouts = await SessionWorkout.filter(session__user_id=target_user.id).count()
#     total_sets = await SetLog.filter(session_workout__session__user_id=target_user.id, is_completed=True).count()

#     set_rows = await SetLog.filter(
#         session_workout__session__user_id=target_user.id,
#         is_completed=True,
#     ).values("weight", "reps")
#     total_volume = round(sum(row["weight"] * row["reps"] for row in set_rows), 2)

#     avg_duration_row = await WorkoutSession.filter(user_id=target_user.id).annotate(
#         avg_duration=Avg("duration_minutes")
#     ).values("avg_duration")
#     avg_duration = round(float(avg_duration_row[0]["avg_duration"] or 0), 2) if avg_duration_row else 0.0

#     workout_rows = await SessionWorkout.filter(session__user_id=target_user.id).values(
#         "estimated_calories_burned",
#         "actual_calories_burned",
#     )
#     total_calories_burned = round(
#         sum((row["actual_calories_burned"] or row["estimated_calories_burned"] or 0) for row in workout_rows),
#         2,
#     )

#     return ProgressSummaryOut(
#         total_workouts=total_workouts,
#         total_sets=total_sets,
#         total_volume=total_volume,
#         avg_duration=avg_duration,
#         total_calories_burned=total_calories_burned,
#     )


# @router.get("/progress/chart", response_model=List[ProgressChartPoint])
# async def progress_chart(
#     user_id: Optional[UUID] = Query(None),
#     current_user: User = Depends(login_required),
# ):
#     target_user = await _resolve_target_user(current_user, user_id, "view")

#     rows = await SetLog.filter(
#         session_workout__session__user_id=target_user.id,
#         is_completed=True,
#     ).values("session_workout__session__date", "weight", "reps")

#     volume_by_date: dict = defaultdict(float)
#     for row in rows:
#         session_date = row["session_workout__session__date"]
#         volume_by_date[session_date] += row["weight"] * row["reps"]

#     return [
#         ProgressChartPoint(date=session_date, volume=round(volume, 2))
#         for session_date, volume in sorted(volume_by_date.items())
#     ]


# @router.get("/progress/bests", response_model=List[ProgressBestOut])
# async def progress_bests(
#     user_id: Optional[UUID] = Query(None),
#     limit: int = Query(3, ge=1, le=20),
#     current_user: User = Depends(login_required),
# ):
#     target_user = await _resolve_target_user(current_user, user_id, "view")

#     rows = await SetLog.filter(
#         session_workout__session__user_id=target_user.id,
#         is_completed=True,
#     ).prefetch_related(
#         "session_workout__workout__equipment",
#         "session_workout__session",
#     ).values(
#         "weight",
#         "reps",
#         "session_workout__workout__id",
#         "session_workout__workout__name",
#         "session_workout__workout__equipment__name",
#         "session_workout__session__date",
#     )

#     bests_by_workout: dict[int, dict] = {}

#     for row in rows:
#         workout_id = row["session_workout__workout__id"]
#         one_rm = _one_rm(row["weight"], row["reps"])
#         current_entry = {
#             "workout_id": workout_id,
#             "workout_name": row["session_workout__workout__name"],
#             "equipment_name": row["session_workout__workout__equipment__name"],
#             "date": row["session_workout__session__date"],
#             "best_1rm": one_rm,
#         }

#         stored = bests_by_workout.get(workout_id)
#         if stored is None:
#             bests_by_workout[workout_id] = {
#                 "best": current_entry,
#                 "previous_best_1rm": 0.0,
#             }
#             continue

#         best = stored["best"]
#         if one_rm > best["best_1rm"] or (
#             one_rm == best["best_1rm"] and row["session_workout__session__date"] > best["date"]
#         ):
#             stored["previous_best_1rm"] = best["best_1rm"]
#             stored["best"] = current_entry
#         elif one_rm > stored["previous_best_1rm"]:
#             stored["previous_best_1rm"] = one_rm

#     ranked = sorted(
#         bests_by_workout.values(),
#         key=lambda item: (item["best"]["best_1rm"], item["best"]["date"]),
#         reverse=True,
#     )[:limit]

#     return [
#         ProgressBestOut(
#             workout_id=item["best"]["workout_id"],
#             workout_name=item["best"]["workout_name"],
#             equipment_name=item["best"]["equipment_name"],
#             date=item["best"]["date"],
#             best_1rm=item["best"]["best_1rm"],
#             previous_best_1rm=round(item["previous_best_1rm"], 2),
#             improvement=round(item["best"]["best_1rm"] - item["previous_best_1rm"], 2),
#         )
#         for item in ranked
#     ]



from collections import defaultdict
from typing import List, Optional
from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from tortoise.functions import Avg

from app.auth import login_required
from applications.session.models import SessionWorkout, SetLog, WorkoutSession
from applications.session.schema import (
    ProgressBestOut,
    ProgressChartPoint,
    ProgressSummaryOut,
)
from applications.user.models import User


router = APIRouter(tags=["Progress"])


# -----------------------------
# Permission Helpers
# -----------------------------
async def _allowed_session_access(current_user: User, target_user: User, action: str) -> bool:
    is_self = current_user.id == target_user.id

    if action == "view":
        if is_self:
            return True
        return current_user.is_superuser or await current_user.has_permission("view_user")

    if action == "manage":
        if is_self:
            return True
        return current_user.is_superuser or await current_user.has_permission("update_user")

    return False


async def _resolve_target_user(current_user: User, user_id: Optional[UUID], action: str) -> User:
    if user_id is None:
        return current_user

    target_user = await User.get_or_none(id=user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not await _allowed_session_access(current_user, target_user, action):
        raise HTTPException(status_code=403, detail="Permission denied.")

    return target_user


# -----------------------------
# Utility
# -----------------------------
def _one_rm(weight: float, reps: int) -> float:
    return round(weight * (1 + (reps / 30)), 2)


def _apply_date_filter(query, start_date: Optional[date], end_date: Optional[date], field: str):
    """
    field examples:
    - "session__date" (SessionWorkout)
    - "session_workout__session__date" (SetLog)
    """
    if start_date:
        query = query.filter(**{f"{field}__gte": start_date})
    if end_date:
        query = query.filter(**{f"{field}__lte": end_date})
    return query


# -----------------------------
# Summary
# -----------------------------
@router.get("/progress/summary", response_model=ProgressSummaryOut)
async def progress_summary(
    user_id: Optional[UUID] = Query(None),
    start_date: Optional[date] = Query(None,  example="2026-04-01"),
    end_date: Optional[date] = Query(None,  example="2026-04-29"),
    current_user: User = Depends(login_required),
):
    target_user = await _resolve_target_user(current_user, user_id, "view")

    # --- SessionWorkout queries ---
    sw_query = SessionWorkout.filter(session__user_id=target_user.id)
    sw_query = _apply_date_filter(sw_query, start_date, end_date, "session__date")

    total_workouts = await sw_query.count()

    # --- SetLog queries ---
    sl_query = SetLog.filter(
        session_workout__session__user_id=target_user.id,
        is_completed=True,
    )
    sl_query = _apply_date_filter(sl_query, start_date, end_date, "session_workout__session__date")

    total_sets = await sl_query.count()

    set_rows = await sl_query.values("weight", "reps")
    total_volume = round(sum(r["weight"] * r["reps"] for r in set_rows), 2)

    # --- WorkoutSession queries ---
    ws_query = WorkoutSession.filter(user_id=target_user.id)
    ws_query = _apply_date_filter(ws_query, start_date, end_date, "date")

    avg_duration_row = await ws_query.annotate(
        avg_duration=Avg("duration_minutes")
    ).values("avg_duration")

    avg_duration = round(float(avg_duration_row[0]["avg_duration"] or 0), 2) if avg_duration_row else 0.0

    # --- Calories ---
    workout_rows = await sw_query.values(
        "estimated_calories_burned",
        "actual_calories_burned",
    )

    total_calories_burned = round(
        sum((r["actual_calories_burned"] or r["estimated_calories_burned"] or 0) for r in workout_rows),
        2,
    )

    return ProgressSummaryOut(
        total_workouts=total_workouts,
        total_sets=total_sets,
        total_volume=total_volume,
        avg_duration=avg_duration,
        total_calories_burned=total_calories_burned,
    )


# -----------------------------
# Chart
# -----------------------------
@router.get("/progress/chart", response_model=List[ProgressChartPoint])
async def progress_chart(
    user_id: Optional[UUID] = Query(None),
    start_date: Optional[date] = Query(None,  example="2026-04-01"),
    end_date: Optional[date] = Query(None,  example="2026-04-29"),
    current_user: User = Depends(login_required),
):
    target_user = await _resolve_target_user(current_user, user_id, "view")

    query = SetLog.filter(
        session_workout__session__user_id=target_user.id,
        is_completed=True,
    )

    query = _apply_date_filter(query, start_date, end_date, "session_workout__session__date")

    rows = await query.values("session_workout__session__date", "weight", "reps")

    volume_by_date: dict = defaultdict(float)

    for row in rows:
        d = row["session_workout__session__date"]
        volume_by_date[d] += row["weight"] * row["reps"]

    return [
        ProgressChartPoint(date=d, volume=round(v, 2))
        for d, v in sorted(volume_by_date.items())
    ]


# -----------------------------
# Bests
# -----------------------------
@router.get("/progress/bests", response_model=List[ProgressBestOut])
async def progress_bests(
    user_id: Optional[UUID] = Query(None),
    limit: int = Query(3, ge=1, le=20),
    start_date: Optional[date] = Query(None,  example="2026-04-01"),
    end_date: Optional[date] = Query(None,  example="2026-04-29"),
    current_user: User = Depends(login_required),
):
    target_user = await _resolve_target_user(current_user, user_id, "view")

    query = SetLog.filter(
        session_workout__session__user_id=target_user.id,
        is_completed=True,
    )

    query = _apply_date_filter(query, start_date, end_date, "session_workout__session__date")

    rows = await query.prefetch_related(
        "session_workout__workout__equipment",
        "session_workout__session",
    ).values(
        "weight",
        "reps",
        "session_workout__workout__id",
        "session_workout__workout__name",
        "session_workout__workout__equipment__name",
        "session_workout__session__date",
    )

    bests_by_workout: dict[int, dict] = {}

    for row in rows:
        workout_id = row["session_workout__workout__id"]
        one_rm = _one_rm(row["weight"], row["reps"])

        current_entry = {
            "workout_id": workout_id,
            "workout_name": row["session_workout__workout__name"],
            "equipment_name": row["session_workout__workout__equipment__name"],
            "date": row["session_workout__session__date"],
            "best_1rm": one_rm,
        }

        stored = bests_by_workout.get(workout_id)

        if stored is None:
            bests_by_workout[workout_id] = {
                "best": current_entry,
                "previous_best_1rm": 0.0,
            }
            continue

        best = stored["best"]

        if one_rm > best["best_1rm"] or (
            one_rm == best["best_1rm"] and current_entry["date"] > best["date"]
        ):
            stored["previous_best_1rm"] = best["best_1rm"]
            stored["best"] = current_entry

        elif one_rm > stored["previous_best_1rm"]:
            stored["previous_best_1rm"] = one_rm

    ranked = sorted(
        bests_by_workout.values(),
        key=lambda x: (x["best"]["best_1rm"], x["best"]["date"]),
        reverse=True,
    )[:limit]

    return [
        ProgressBestOut(
            workout_id=item["best"]["workout_id"],
            workout_name=item["best"]["workout_name"],
            equipment_name=item["best"]["equipment_name"],
            date=item["best"]["date"],
            best_1rm=item["best"]["best_1rm"],
            previous_best_1rm=round(item["previous_best_1rm"], 2),
            improvement=round(item["best"]["best_1rm"] - item["previous_best_1rm"], 2),
        )
        for item in ranked
    ]