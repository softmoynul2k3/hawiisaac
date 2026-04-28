from collections import defaultdict
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from tortoise.functions import Avg
from tortoise.queryset import QuerySet

from app.auth import login_required
from app.utils.datetime_formatter import to_utc_z
from applications.content.models import Content
from applications.equipments.models import Workout, WorkoutType
from applications.session.models import CardioLog, SessionStatus, SessionWorkout, SetLog, WorkoutSession
from applications.session.schema import (
    ActiveSessionOut,
    CardioLogCreate,
    CardioLogOut,
    ProgressBestOut,
    ProgressChartPoint,
    ProgressSummaryOut,
    SessionComplete,
    SessionWorkoutComplete,
    SessionWorkoutCreate,
    SessionWorkoutOut,
    SetLogCreate,
    SetLogOut,
    WorkoutSessionCreate,
    WorkoutSessionOut,
)
from applications.user.models import User


router = APIRouter(tags=["Workout Sessions"])


def _utc_now():
    return datetime.now(timezone.utc)


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


async def _get_accessible_session_workout(session_workout_id: int, current_user: User, action: str) -> SessionWorkout:
    session_workout = await SessionWorkout.get_or_none(id=session_workout_id).prefetch_related("session__user", "workout")
    if not session_workout:
        raise HTTPException(status_code=404, detail="Session workout not found")

    if not await _allowed_session_access(current_user, session_workout.session.user, action):
        raise HTTPException(status_code=403, detail="Permission denied.")

    return session_workout


def _set_volume(weight: float, reps: int) -> float:
    return round(weight * reps, 2)


def _one_rm(weight: float, reps: int) -> float:
    return round(weight * (1 + (reps / 30)), 2)


def _resolve_weight_kg(session: WorkoutSession, explicit_weight_kg: Optional[float] = None) -> float:
    return round(float(explicit_weight_kg or session.user_weight_kg or 70.0), 2)


def _calculate_calories_burned(met_value: float, time_minutes: float, user_weight_kg: float) -> float:
    calories = (met_value * 3.5 * user_weight_kg / 200) * time_minutes
    return round(calories, 2)


def _serialize_cardio_log(cardio_log: CardioLog | None) -> CardioLogOut | None:
    if cardio_log is None:
        return None

    return CardioLogOut(
        id=cardio_log.id,
        time_minutes=cardio_log.time_minutes,
        distance=cardio_log.distance,
        speed=cardio_log.speed,
        incline=cardio_log.incline,
        calories_burned=round(cardio_log.calories_burned, 2),
        user_weight_kg=cardio_log.user_weight_kg,
    )


async def _resolve_cardio_log(session_workout: SessionWorkout) -> CardioLog | None:
    cardio_log = getattr(session_workout, "cardio_log", None)
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
        duration_seconds=set_log.duration_seconds,
        is_completed=set_log.is_completed,
        volume=_set_volume(set_log.weight, set_log.reps),
        one_rm=_one_rm(set_log.weight, set_log.reps),
    )


def _serialize_workout_reference(workout: Workout) -> dict:
    return {
        "id": workout.id,
        "name": workout.name,
        "workout_type": workout.workout_type,
        "met_value": workout.met_value,
        "sets": workout.sets,
        "reps": workout.reps,
        "rest": workout.rest,
    }


async def _serialize_session_workout(session_workout: SessionWorkout) -> SessionWorkoutOut:
    cardio_log = await _resolve_cardio_log(session_workout)
    return SessionWorkoutOut(
        id=session_workout.id,
        order=session_workout.order,
        workout=_serialize_workout_reference(session_workout.workout),
        content={
            "id": session_workout.content.id,
            "title": session_workout.content.title,
        } if session_workout.content else None,
        note=session_workout.note,
        is_completed=session_workout.is_completed,
        estimated_calories_burned=round(session_workout.estimated_calories_burned, 2),
        actual_calories_burned=round(session_workout.actual_calories_burned, 2),
        set_logs=[_serialize_set_log(set_log) for set_log in session_workout.set_logs],
        cardio_log=_serialize_cardio_log(cardio_log),
    )


def _session_total_calories(session: WorkoutSession) -> float:
    return round(
        sum((workout.actual_calories_burned or workout.estimated_calories_burned or 0) for workout in session.workouts),
        2,
    )


async def _serialize_session(session: WorkoutSession) -> WorkoutSessionOut:
    return WorkoutSessionOut(
        id=session.id,
        user_id=session.user_id,
        date=session.date,
        duration_minutes=session.duration_minutes,
        note=session.note,
        user_weight_kg=session.user_weight_kg,
        status=session.status,
        current_workout_order=session.current_workout_order,
        total_calories_burned=_session_total_calories(session),
        created_at=to_utc_z(session.created_at) or "",
        updated_at=to_utc_z(session.updated_at) or "",
        completed_at=to_utc_z(session.completed_at),
        workouts=[await _serialize_session_workout(session_workout) for session_workout in session.workouts],
    )


async def _load_full_session(session_id: int):
    session = await WorkoutSession.get(id=session_id).prefetch_related(
        "workouts__workout",
        "workouts__set_logs",
        "workouts__cardio_log"
    )

    workouts = await session.workouts.all().order_by("order", "id")

    return {
        "session": session,
        "workouts": workouts
    }


def _get_current_session_workout_from_loaded_session(session: WorkoutSession) -> SessionWorkout | None:
    for item in session.workouts:
        if not item.is_completed:
            return item
    return session.workouts[0] if session.workouts else None


async def _get_active_session_for_user(user_id) -> WorkoutSession | None:
    session = await WorkoutSession.filter(user_id=user_id, status=SessionStatus.ACTIVE).order_by("-created_at").first()
    if session is None:
        return None
    return await _load_full_session(session.id)


async def _ensure_session_is_active(session: WorkoutSession):
    if session.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is already completed")


async def _update_session_progress(session: WorkoutSession) -> WorkoutSession:
    loaded_session = await _load_full_session(session.id)
    current_item = _get_current_session_workout_from_loaded_session(loaded_session)
    next_order = current_item.order if current_item else 1
    updates = []
    if loaded_session.current_workout_order != next_order:
        loaded_session.current_workout_order = next_order
        updates.append("current_workout_order")
    if updates:
        await loaded_session.save(update_fields=[*updates, "updated_at"])
        loaded_session = await _load_full_session(loaded_session.id)
    return loaded_session


async def _create_or_reuse_active_session(current_user: User, *, date, duration_minutes: int = 1) -> tuple[WorkoutSession, bool]:
    active_session = await _get_active_session_for_user(current_user.id)
    if active_session is not None:
        active_session = await _update_session_progress(active_session)
        return active_session, False

    session = await WorkoutSession.create(
        user=current_user,
        date=date,
        duration_minutes=duration_minutes,
        current_workout_order=1,
    )
    session = await _load_full_session(session.id)
    return session, True


async def _ensure_workout_has_logs(session_workout: SessionWorkout):
    await session_workout.fetch_related("workout", "set_logs", "cardio_log")
    if session_workout.workout.workout_type == WorkoutType.NON_CARDIO:
        if not any(set_log.is_completed for set_log in session_workout.set_logs):
            raise HTTPException(status_code=400, detail="Cannot complete workout without logs")
        return
    if await _resolve_cardio_log(session_workout) is None:
        raise HTTPException(status_code=400, detail="Cannot complete workout without logs")


async def _create_session_workout(
    session: WorkoutSession,
    workout_id: int,
    *,
    content_id: Optional[int] = None,
    note: Optional[str] = None,
    order: Optional[int] = None,
) -> SessionWorkout:
    workout = await Workout.get_or_none(id=workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    content = None
    if content_id is not None:
        content = await Content.get_or_none(id=content_id).prefetch_related("workouts")
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")
        linked_workout_ids = {item.id for item in content.workouts}
        if linked_workout_ids and workout.id not in linked_workout_ids:
            raise HTTPException(status_code=400, detail="Selected workout does not match the linked content workouts")

    if order is None:
        last_item = await SessionWorkout.filter(session_id=session.id).order_by("-order").first()
        order = 1 if last_item is None else last_item.order + 1
    elif await SessionWorkout.filter(session_id=session.id, order=order).exists():
        raise HTTPException(status_code=400, detail="Workout order already exists in this session")

    return await SessionWorkout.create(
        session=session,
        workout=workout,
        content=content,
        order=order,
        note=(note or "").strip() or None,
    )


async def _refresh_session_workout_calories(session_workout: SessionWorkout) -> SessionWorkout:
    await session_workout.fetch_related("session", "workout", "set_logs", "cardio_log")

    if session_workout.workout.workout_type == WorkoutType.CARDIO:
        cardio_log = await _resolve_cardio_log(session_workout)
        session_workout.estimated_calories_burned = 0
        session_workout.actual_calories_burned = round(cardio_log.calories_burned, 2) if cardio_log else 0
    else:
        total_seconds = sum(set_log.duration_seconds for set_log in session_workout.set_logs if set_log.is_completed)
        minutes = total_seconds / 60 if total_seconds else 0
        weight_kg = _resolve_weight_kg(session_workout.session)
        session_workout.estimated_calories_burned = _calculate_calories_burned(
            session_workout.workout.met_value,
            minutes,
            weight_kg,
        ) if minutes else 0
        session_workout.actual_calories_burned = session_workout.estimated_calories_burned

    await session_workout.save(update_fields=["estimated_calories_burned", "actual_calories_burned", "updated_at"])
    return session_workout


async def _mark_session_complete_if_needed(session: WorkoutSession):
    remaining = await SessionWorkout.filter(session_id=session.id, is_completed=False).count()
    if remaining == 0:
        session.status = SessionStatus.COMPLETED
        session.current_workout_order = 0
        session.completed_at = _utc_now()
        await session.save(update_fields=["status", "current_workout_order", "completed_at", "updated_at"])
        return
    await _update_session_progress(session)


@router.post("/sessions", response_model=WorkoutSessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(payload: WorkoutSessionCreate, current_user: User = Depends(login_required)):
    active_session = await _get_active_session_for_user(current_user.id)
    if active_session is not None:
        return await _serialize_session(active_session)

    session = await WorkoutSession.create(
        user=current_user,
        date=payload.date,
        duration_minutes=payload.duration_minutes,
        note=(payload.note or "").strip() or None,
        user_weight_kg=payload.user_weight_kg,
        current_workout_order=1,
    )

    for index, item in enumerate(payload.workouts, start=1):
        await _create_session_workout(
            session,
            item.workout_id,
            content_id=item.content_id,
            note=item.note,
            order=item.order or index,
        )

    session = await _load_full_session(session.id)
    session = await _update_session_progress(session)
    return await _serialize_session(session)


@router.get("/sessions", response_model=List[WorkoutSessionOut])
async def list_sessions(
    user_id: Optional[UUID] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(login_required),
):
    target_user = await _resolve_target_user(current_user, user_id, "view")

    sessions = await WorkoutSession.filter(user_id=target_user.id).offset(offset).limit(limit)
    loaded_sessions = [await _load_full_session(session.id) for session in sessions]
    return [
        await _serialize_session(item["session"])
        for item in loaded_sessions
    ]


@router.get("/sessions/active", response_model=ActiveSessionOut)
async def get_active_session(current_user: User = Depends(login_required)):
    active_session = await _get_active_session_for_user(current_user.id)
    if active_session is None:
        raise HTTPException(status_code=404, detail="Active session not found")
    active_session = await _update_session_progress(active_session)
    current_item = _get_current_session_workout_from_loaded_session(active_session)
    return ActiveSessionOut(
        session=await _serialize_session(active_session),
        current_session_workout=await _serialize_session_workout(current_item) if current_item else None,
    )


@router.get("/sessions/{session_id}", response_model=WorkoutSessionOut)
async def get_session(session_id: int, current_user: User = Depends(login_required)):
    await _get_accessible_session(session_id, current_user, "view")
    session = await _load_full_session(session_id)
    return await _serialize_session(session)


@router.post("/sessions/{session_id}/workouts", response_model=SessionWorkoutOut, status_code=status.HTTP_201_CREATED)
async def add_session_workout(
    session_id: int,
    payload: SessionWorkoutCreate,
    current_user: User = Depends(login_required),
):
    if payload.session_id != session_id:
        raise HTTPException(status_code=400, detail="Session id mismatch")

    session = await _get_accessible_session(session_id, current_user, "manage")
    await _ensure_session_is_active(session)
    session_workout = await _create_session_workout(
        session,
        payload.workout_id,
        content_id=payload.content_id,
        note=payload.note,
        order=payload.order,
    )
    session = await _load_full_session(session.id)
    session = await _update_session_progress(session)
    created_item = next(item for item in session.workouts if item.id == session_workout.id)
    return await _serialize_session_workout(created_item)


@router.post("/session-workouts/{session_workout_id}/complete", response_model=SessionWorkoutOut)
async def complete_session_workout(
    session_workout_id: int,
    payload: SessionWorkoutComplete,
    current_user: User = Depends(login_required),
):
    session_workout = await _get_accessible_session_workout(session_workout_id, current_user, "manage")
    await _ensure_session_is_active(session_workout.session)
    await _ensure_workout_has_logs(session_workout)
    session_workout.note = (payload.note or session_workout.note or "").strip() or None
    session_workout.is_completed = True
    session_workout.completed_at = _utc_now()
    await session_workout.save(update_fields=["note", "is_completed", "completed_at", "updated_at"])

    if payload.mark_session_complete_if_finished:
        await _mark_session_complete_if_needed(session_workout.session)

    session = await _load_full_session(session_workout.session_id)
    item = next(item for item in session.workouts if item.id == session_workout_id)
    return await _serialize_session_workout(item)


@router.post("/sessions/{session_id}/complete", response_model=WorkoutSessionOut)
async def complete_session(
    session_id: int,
    payload: SessionComplete,
    current_user: User = Depends(login_required),
):
    session = await _get_accessible_session(session_id, current_user, "manage")
    await _ensure_session_is_active(session)
    if payload.duration_minutes is not None:
        session.duration_minutes = payload.duration_minutes
    if payload.note is not None:
        session.note = payload.note.strip() or None
    session.status = SessionStatus.COMPLETED
    session.current_workout_order = 0
    session.completed_at = _utc_now()
    await session.save(update_fields=["duration_minutes", "note", "status", "current_workout_order", "completed_at", "updated_at"])

    loaded_session = await _load_full_session(session.id)
    return await _serialize_session(loaded_session)


@router.post("/set-log", response_model=SetLogOut, status_code=status.HTTP_201_CREATED)
async def create_set_log(payload: SetLogCreate, current_user: User = Depends(login_required)):
    session_workout = await _get_accessible_session_workout(payload.session_workout_id, current_user, "manage")
    await _ensure_session_is_active(session_workout.session)

    if session_workout.workout.workout_type == WorkoutType.CARDIO:
        raise HTTPException(status_code=400, detail="Set logs are only allowed for non-cardio workouts")

    set_log = await SetLog.get_or_none(session_workout_id=payload.session_workout_id, order=payload.order)
    if set_log is None:
        set_log = await SetLog.create(
            session_workout=session_workout,
            weight=payload.weight,
            reps=payload.reps,
            order=payload.order,
            duration_seconds=payload.duration_seconds,
            is_completed=payload.is_completed,
        )
    else:
        set_log.weight = payload.weight
        set_log.reps = payload.reps
        set_log.duration_seconds = payload.duration_seconds
        set_log.is_completed = payload.is_completed
        await set_log.save(update_fields=["weight", "reps", "duration_seconds", "is_completed", "updated_at"])

    await _refresh_session_workout_calories(session_workout)
    await _update_session_progress(session_workout.session)
    return _serialize_set_log(set_log)


@router.post("/cardio-log", response_model=CardioLogOut, status_code=status.HTTP_201_CREATED)
async def create_cardio_log(payload: CardioLogCreate, current_user: User = Depends(login_required)):
    session_workout = await _get_accessible_session_workout(payload.session_workout_id, current_user, "manage")
    await _ensure_session_is_active(session_workout.session)

    if session_workout.workout.workout_type != WorkoutType.CARDIO:
        raise HTTPException(status_code=400, detail="Cardio logs are only allowed for cardio workouts")

    await session_workout.fetch_related("session", "workout")
    weight_kg = _resolve_weight_kg(session_workout.session, payload.user_weight_kg)
    calories_burned = _calculate_calories_burned(
        session_workout.workout.met_value,
        payload.time_minutes,
        weight_kg,
    )

    cardio_log = await CardioLog.get_or_none(session_workout_id=payload.session_workout_id)
    if cardio_log is None:
        cardio_log = await CardioLog.create(
            session_workout=session_workout,
            time_minutes=payload.time_minutes,
            distance=payload.distance,
            speed=payload.speed,
            incline=payload.incline,
            calories_burned=calories_burned,
            user_weight_kg=weight_kg,
        )
    else:
        cardio_log.time_minutes = payload.time_minutes
        cardio_log.distance = payload.distance
        cardio_log.speed = payload.speed
        cardio_log.incline = payload.incline
        cardio_log.calories_burned = calories_burned
        cardio_log.user_weight_kg = weight_kg
        await cardio_log.save(update_fields=["time_minutes", "distance", "speed", "incline", "calories_burned", "user_weight_kg", "updated_at"])

    await _refresh_session_workout_calories(session_workout)
    await _update_session_progress(session_workout.session)
    return _serialize_cardio_log(cardio_log)


@router.get("/progress/summary", response_model=ProgressSummaryOut)
async def progress_summary(
    user_id: Optional[UUID] = Query(None),
    current_user: User = Depends(login_required),
):
    target_user = await _resolve_target_user(current_user, user_id, "view")

    total_workouts = await SessionWorkout.filter(session__user_id=target_user.id).count()
    total_sets = await SetLog.filter(session_workout__session__user_id=target_user.id, is_completed=True).count()

    set_rows = await SetLog.filter(
        session_workout__session__user_id=target_user.id,
        is_completed=True,
    ).values("weight", "reps")
    total_volume = round(sum(row["weight"] * row["reps"] for row in set_rows), 2)

    avg_duration_row = await WorkoutSession.filter(user_id=target_user.id).annotate(
        avg_duration=Avg("duration_minutes")
    ).values("avg_duration")
    avg_duration = round(float(avg_duration_row[0]["avg_duration"] or 0), 2) if avg_duration_row else 0.0

    workout_rows = await SessionWorkout.filter(session__user_id=target_user.id).values(
        "estimated_calories_burned",
        "actual_calories_burned",
    )
    total_calories_burned = round(
        sum((row["actual_calories_burned"] or row["estimated_calories_burned"] or 0) for row in workout_rows),
        2,
    )

    return ProgressSummaryOut(
        total_workouts=total_workouts,
        total_sets=total_sets,
        total_volume=total_volume,
        avg_duration=avg_duration,
        total_calories_burned=total_calories_burned,
    )


@router.get("/progress/chart", response_model=List[ProgressChartPoint])
async def progress_chart(
    user_id: Optional[UUID] = Query(None),
    current_user: User = Depends(login_required),
):
    target_user = await _resolve_target_user(current_user, user_id, "view")

    rows = await SetLog.filter(
        session_workout__session__user_id=target_user.id,
        is_completed=True,
    ).values("session_workout__session__date", "weight", "reps")

    volume_by_date: dict = defaultdict(float)
    for row in rows:
        session_date = row["session_workout__session__date"]
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
        session_workout__session__user_id=target_user.id,
        is_completed=True,
    ).prefetch_related(
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
            one_rm == best["best_1rm"] and row["session_workout__session__date"] > best["date"]
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
