from collections import defaultdict
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from tortoise.functions import Avg

from app.auth import login_required
from applications.session.models import SessionWorkout, SetLog, WorkoutSession
from applications.session.schema import (
    ProgressBestOut,
    ProgressChartPoint,
    ProgressHighlightsOut,
    ProgressSummaryOut,
    RecentActivityItemOut,
)
from applications.user.models import User


router = APIRouter(tags=["Progress"])


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


def _validate_date_range(start_date: Optional[date], end_date: Optional[date]) -> None:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")


def _one_rm(weight: float, reps: int) -> float:
    return round(weight * (1 + (reps / 30)), 2)


def _apply_date_filter(query, start_date: Optional[date], end_date: Optional[date], field: str):
    if start_date:
        query = query.filter(**{f"{field}__gte": start_date})
    if end_date:
        query = query.filter(**{f"{field}__lte": end_date})
    return query


def _safe_number(value: Optional[float | int]) -> float:
    return float(value or 0)


def _calculate_days_streak(session_dates: list[date]) -> int:
    if not session_dates:
        return 0

    unique_dates = sorted(set(session_dates), reverse=True)
    today = date.today()
    latest_date = unique_dates[0]

    if latest_date not in {today, today - timedelta(days=1)}:
        return 0

    streak = 1
    previous_date = latest_date

    for current_date in unique_dates[1:]:
        if previous_date - current_date == timedelta(days=1):
            streak += 1
            previous_date = current_date
            continue
        if current_date == previous_date:
            continue
        break

    return streak


def _relative_day_label(target_date: date) -> str:
    days_diff = (date.today() - target_date).days

    if days_diff <= 0:
        return "Today"
    if days_diff == 1:
        return "Yesterday"
    return f"{days_diff} days ago"


@router.get("/progress/highlights", response_model=ProgressHighlightsOut)
async def progress_highlights(
    user_id: Optional[UUID] = Query(None),
    current_user: User = Depends(login_required),
):
    target_user = await _resolve_target_user(current_user, user_id, "view")

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    session_rows = await WorkoutSession.filter(user_id=target_user.id).values("date")
    session_dates = [row["date"] for row in session_rows if row["date"] is not None]

    workouts_this_week = await WorkoutSession.filter(
        user_id=target_user.id,
        date__gte=week_start,
        date__lte=week_end,
    ).count()

    workout_rows = await SessionWorkout.filter(session__user_id=target_user.id).values(
        "estimated_calories_burned",
        "actual_calories_burned",
    )
    calories_burned = round(
        sum(
            _safe_number(row["actual_calories_burned"]) or _safe_number(row["estimated_calories_burned"])
            for row in workout_rows
        ),
        2,
    )

    return ProgressHighlightsOut(
        days_streak=_calculate_days_streak(session_dates),
        workouts_this_week=workouts_this_week,
        calories_burned=calories_burned,
    )


@router.get("/progress/recent-activity", response_model=list[RecentActivityItemOut])
async def progress_recent_activity(
    user_id: Optional[UUID] = Query(None),
    limit: int = Query(3, ge=1, le=20),
    current_user: User = Depends(login_required),
):
    target_user = await _resolve_target_user(current_user, user_id, "view")

    sessions = await WorkoutSession.filter(user_id=target_user.id).order_by("-date", "-created_at").limit(limit)
    results: list[RecentActivityItemOut] = []

    for session in sessions:
        workouts = await SessionWorkout.filter(session_id=session.id).order_by("order", "id").values(
            "workout__name",
            "note",
        )
        set_count = await SetLog.filter(
            session_workout__session_id=session.id,
            is_completed=True,
        ).count()

        title = session.note or ""
        if not title and workouts:
            title = workouts[0]["note"] or workouts[0]["workout__name"] or ""
        if not title:
            title = f"Workout Session {session.id}"

        results.append(
            RecentActivityItemOut(
                session_id=session.id,
                title=title,
                date=session.date,
                day_label=_relative_day_label(session.date),
                duration_minutes=session.duration_minutes,
                set_count=set_count,
            )
        )

    return results


@router.get("/progress/summary", response_model=ProgressSummaryOut)
async def progress_summary(
    user_id: Optional[UUID] = Query(None),
    start_date: Optional[date] = Query(None, example="2026-04-01"),
    end_date: Optional[date] = Query(None, example="2026-04-29"),
    current_user: User = Depends(login_required),
):
    _validate_date_range(start_date, end_date)
    target_user = await _resolve_target_user(current_user, user_id, "view")

    session_workout_query = SessionWorkout.filter(session__user_id=target_user.id)
    session_workout_query = _apply_date_filter(session_workout_query, start_date, end_date, "session__date")

    set_log_query = SetLog.filter(
        session_workout__session__user_id=target_user.id,
        is_completed=True,
    )
    set_log_query = _apply_date_filter(
        set_log_query,
        start_date,
        end_date,
        "session_workout__session__date",
    )

    workout_session_query = WorkoutSession.filter(user_id=target_user.id)
    workout_session_query = _apply_date_filter(workout_session_query, start_date, end_date, "date")

    total_workouts = await session_workout_query.count()
    total_sets = await set_log_query.count()

    set_rows = await set_log_query.values("weight", "reps")
    total_volume = round(
        sum(_safe_number(row["weight"]) * _safe_number(row["reps"]) for row in set_rows),
        2,
    )

    avg_duration_row = await workout_session_query.annotate(avg_duration=Avg("duration_minutes")).values("avg_duration")
    avg_duration = round(_safe_number(avg_duration_row[0]["avg_duration"]) if avg_duration_row else 0, 2)

    workout_rows = await session_workout_query.values(
        "estimated_calories_burned",
        "actual_calories_burned",
    )
    total_calories_burned = round(
        sum(
            _safe_number(row["actual_calories_burned"]) or _safe_number(row["estimated_calories_burned"])
            for row in workout_rows
        ),
        2,
    )

    return ProgressSummaryOut(
        total_workouts=total_workouts,
        total_sets=total_sets,
        total_volume=total_volume,
        avg_duration=avg_duration,
        total_calories_burned=total_calories_burned,
    )


@router.get("/progress/chart", response_model=list[ProgressChartPoint])
async def progress_chart(
    user_id: Optional[UUID] = Query(None),
    start_date: Optional[date] = Query(None, example="2026-04-01"),
    end_date: Optional[date] = Query(None, example="2026-04-29"),
    current_user: User = Depends(login_required),
):
    _validate_date_range(start_date, end_date)
    target_user = await _resolve_target_user(current_user, user_id, "view")

    query = SetLog.filter(
        session_workout__session__user_id=target_user.id,
        is_completed=True,
    )
    query = _apply_date_filter(query, start_date, end_date, "session_workout__session__date")

    rows = await query.values("session_workout__session__date", "weight", "reps")
    volume_by_date: dict[date, float] = defaultdict(float)

    for row in rows:
        session_date = row["session_workout__session__date"]
        if session_date is None:
            continue
        volume_by_date[session_date] += _safe_number(row["weight"]) * _safe_number(row["reps"])

    return [
        ProgressChartPoint(date=session_date, volume=round(volume, 2))
        for session_date, volume in sorted(volume_by_date.items())
    ]


@router.get("/progress/bests", response_model=list[ProgressBestOut])
async def progress_bests(
    user_id: Optional[UUID] = Query(None),
    limit: int = Query(3, ge=1, le=20),
    start_date: Optional[date] = Query(None, example="2026-04-01"),
    end_date: Optional[date] = Query(None, example="2026-04-29"),
    current_user: User = Depends(login_required),
):
    _validate_date_range(start_date, end_date)
    target_user = await _resolve_target_user(current_user, user_id, "view")

    query = SetLog.filter(
        session_workout__session__user_id=target_user.id,
        is_completed=True,
    )
    query = _apply_date_filter(query, start_date, end_date, "session_workout__session__date")

    rows = await query.values(
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
        session_date = row["session_workout__session__date"]
        if workout_id is None or session_date is None:
            continue

        one_rm = _one_rm(_safe_number(row["weight"]), int(row["reps"] or 0))
        current_entry = {
            "workout_id": workout_id,
            "workout_name": row["session_workout__workout__name"],
            "equipment_name": row["session_workout__workout__equipment__name"],
            "date": session_date,
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
        if one_rm > best["best_1rm"] or (one_rm == best["best_1rm"] and session_date > best["date"]):
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
