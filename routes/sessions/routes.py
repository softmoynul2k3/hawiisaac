from collections import defaultdict
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from tortoise.queryset import QuerySet
from tortoise.functions import Avg

from app.auth import login_required
from app.utils.datetime_formatter import to_utc_z
from applications.equipments.models import Workout
from applications.session.models import CardioLog, SetLog, WorkoutLog, WorkoutSession
from applications.session.schema import (
    CardioLogCreate,
    CardioLogOut,
    ProgressBestOut,
    ProgressChartPoint,
    ProgressSummaryOut,
    SetLogCreate,
    SetLogOut,
    WorkoutLogCreate,
    WorkoutLogOut,
    WorkoutSessionCreate,
    WorkoutSessionOut,
)
from applications.user.models import User


router = APIRouter(tags=["Workout Sessions"])


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


async def _get_accessible_session(session_id: int, current_user: User, action: str) -> WorkoutSession:
    session = await WorkoutSession.get_or_none(id=session_id).prefetch_related("user")
    if not session:
        raise HTTPException(status_code=404, detail="Workout session not found")

    if not await _allowed_session_access(current_user, session.user, action):
        raise HTTPException(status_code=403, detail="Permission denied.")

    return session


async def _get_accessible_workout_log(workout_log_id: int, current_user: User, action: str) -> WorkoutLog:
    workout_log = await WorkoutLog.get_or_none(id=workout_log_id).prefetch_related("session__user", "workout")
    if not workout_log:
        raise HTTPException(status_code=404, detail="Workout log not found")

    if not await _allowed_session_access(current_user, workout_log.session.user, action):
        raise HTTPException(status_code=403, detail="Permission denied.")

    return workout_log


def _set_volume(weight: float, reps: int) -> float:
    return round(weight * reps, 2)


def _one_rm(weight: float, reps: int) -> float:
    return round(weight * (1 + (reps / 30)), 2)


def _serialize_cardio_log(cardio_log: CardioLog | None) -> CardioLogOut | None:
    if cardio_log is None:
        return None

    return CardioLogOut(
        id=cardio_log.id,
        time_minutes=cardio_log.time_minutes,
        distance=cardio_log.distance,
        speed=cardio_log.speed,
        incline=cardio_log.incline,
    )


async def _resolve_cardio_log(workout_log: WorkoutLog) -> CardioLog | None:
    cardio_log = getattr(workout_log, "cardio_log", None)
    if cardio_log is None:
        return None
    if isinstance(cardio_log, QuerySet):
        return await cardio_log.first()
    return cardio_log


def _serialize_set_log(set_log: SetLog) -> SetLogOut:
    return SetLogOut(
        id=set_log.id,
        weight=set_log.weight,
        reps=set_log.reps,
        order=set_log.order,
        is_completed=set_log.is_completed,
        volume=_set_volume(set_log.weight, set_log.reps),
        one_rm=_one_rm(set_log.weight, set_log.reps),
    )


async def _serialize_workout_log(workout_log: WorkoutLog) -> WorkoutLogOut:
    cardio_log = await _resolve_cardio_log(workout_log)
    return WorkoutLogOut(
        id=workout_log.id,
        workout={
            "id": workout_log.workout.id,
            "name": workout_log.workout.name,
        },
        note=workout_log.note,
        set_logs=[_serialize_set_log(set_log) for set_log in workout_log.set_logs],
        cardio_log=_serialize_cardio_log(cardio_log),
    )


async def _serialize_session(session: WorkoutSession) -> WorkoutSessionOut:
    return WorkoutSessionOut(
        id=session.id,
        user_id=session.user_id,
        date=session.date,
        duration_minutes=session.duration_minutes,
        created_at=to_utc_z(session.created_at) or "",
        workout_logs=[await _serialize_workout_log(workout_log) for workout_log in session.workout_logs],
    )


@router.post("/sessions", response_model=WorkoutSessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(payload: WorkoutSessionCreate, current_user: User = Depends(login_required)):
    session = await WorkoutSession.create(
        user=current_user,
        date=payload.date,
        duration_minutes=payload.duration_minutes,
    )

    await session.fetch_related("workout_logs")
    return await _serialize_session(session)


@router.get("/sessions", response_model=List[WorkoutSessionOut])
async def list_sessions(
    user_id: Optional[UUID] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(login_required),
):
    target_user = await _resolve_target_user(current_user, user_id, "view")

    sessions = await WorkoutSession.filter(user_id=target_user.id).prefetch_related(
        "workout_logs__workout",
        "workout_logs__set_logs",
        "workout_logs__cardio_log",
    ).offset(offset).limit(limit)

    return [await _serialize_session(session) for session in sessions]


@router.post("/workout-log", response_model=WorkoutLogOut, status_code=status.HTTP_201_CREATED)
async def create_workout_log(payload: WorkoutLogCreate, current_user: User = Depends(login_required)):
    session = await _get_accessible_session(payload.session_id, current_user, "manage")

    workout = await Workout.get_or_none(id=payload.workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    workout_log = await WorkoutLog.create(
        session=session,
        workout=workout,
        note=(payload.note or "").strip() or None,
    )

    await workout_log.fetch_related("workout", "content", "set_logs")
    return await _serialize_workout_log(workout_log)


@router.post("/set-log", response_model=SetLogOut, status_code=status.HTTP_201_CREATED)
async def create_set_log(payload: SetLogCreate, current_user: User = Depends(login_required)):
    workout_log = await _get_accessible_workout_log(payload.workout_log_id, current_user, "manage")

    exists = await SetLog.filter(workout_log_id=payload.workout_log_id, order=payload.order).exists()
    if exists:
        raise HTTPException(status_code=400, detail="Set order already exists for this workout log")

    set_log = await SetLog.create(
        workout_log=workout_log,
        weight=payload.weight,
        reps=payload.reps,
        order=payload.order,
        is_completed=payload.is_completed,
    )

    return _serialize_set_log(set_log)


@router.post("/cardio-log", response_model=CardioLogOut, status_code=status.HTTP_201_CREATED)
async def create_cardio_log(payload: CardioLogCreate, current_user: User = Depends(login_required)):
    workout_log = await _get_accessible_workout_log(payload.workout_log_id, current_user, "manage")

    if await CardioLog.filter(workout_log_id=payload.workout_log_id).exists():
        raise HTTPException(status_code=400, detail="Cardio log already exists for this workout log")

    cardio_log = await CardioLog.create(
        workout_log=workout_log,
        time_minutes=payload.time_minutes,
        distance=payload.distance,
        speed=payload.speed,
        incline=payload.incline,
    )

    return _serialize_cardio_log(cardio_log)


@router.get("/progress/summary", response_model=ProgressSummaryOut)
async def progress_summary(
    user_id: Optional[UUID] = Query(None),
    current_user: User = Depends(login_required),
):
    target_user = await _resolve_target_user(current_user, user_id, "view")

    total_workouts = await WorkoutLog.filter(session__user_id=target_user.id).count()
    total_sets = await SetLog.filter(workout_log__session__user_id=target_user.id, is_completed=True).count()

    set_rows = await SetLog.filter(
        workout_log__session__user_id=target_user.id,
        is_completed=True,
    ).values("weight", "reps")
    total_volume = round(sum(row["weight"] * row["reps"] for row in set_rows), 2)

    avg_duration_row = await WorkoutSession.filter(user_id=target_user.id).annotate(
        avg_duration=Avg("duration_minutes")
    ).values("avg_duration")
    avg_duration = round(float(avg_duration_row[0]["avg_duration"] or 0), 2) if avg_duration_row else 0.0

    return ProgressSummaryOut(
        total_workouts=total_workouts,
        total_sets=total_sets,
        total_volume=total_volume,
        avg_duration=avg_duration,
    )


@router.get("/progress/chart", response_model=List[ProgressChartPoint])
async def progress_chart(
    user_id: Optional[UUID] = Query(None),
    current_user: User = Depends(login_required),
):
    target_user = await _resolve_target_user(current_user, user_id, "view")

    rows = await SetLog.filter(
        workout_log__session__user_id=target_user.id,
        is_completed=True,
    ).values("workout_log__session__date", "weight", "reps")

    volume_by_date: dict = defaultdict(float)
    for row in rows:
        session_date = row["workout_log__session__date"]
        volume_by_date[session_date] += row["weight"] * row["reps"]

    return [
        ProgressChartPoint(date=session_date, volume=round(volume, 2))
        for session_date, volume in sorted(volume_by_date.items())
    ]


@router.get("/progress/bests", response_model=List[ProgressBestOut])
async def progress_bests(
    user_id: Optional[UUID] = Query(None),
    limit: int = Query(3, ge=1, le=20),
    current_user: User = Depends(login_required),
):
    target_user = await _resolve_target_user(current_user, user_id, "view")

    rows = await SetLog.filter(
        workout_log__session__user_id=target_user.id,
        is_completed=True,
    ).prefetch_related(
        "workout_log__workout__equipment",
        "workout_log__session",
    ).values(
        "weight",
        "reps",
        "workout_log__workout__id",
        "workout_log__workout__name",
        "workout_log__workout__equipment__name",
        "workout_log__session__date",
    )

    bests_by_workout: dict[int, dict] = {}

    for row in rows:
        workout_id = row["workout_log__workout__id"]
        one_rm = _one_rm(row["weight"], row["reps"])
        current_entry = {
            "workout_id": workout_id,
            "workout_name": row["workout_log__workout__name"],
            "equipment_name": row["workout_log__workout__equipment__name"],
            "date": row["workout_log__session__date"],
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
            one_rm == best["best_1rm"] and row["workout_log__session__date"] > best["date"]
        ):
            stored["previous_best_1rm"] = best["best_1rm"]
            stored["best"] = current_entry
        elif one_rm > stored["previous_best_1rm"]:
            stored["previous_best_1rm"] = one_rm

    ranked = sorted(
        bests_by_workout.values(),
        key=lambda item: (item["best"]["best_1rm"], item["best"]["date"]),
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
