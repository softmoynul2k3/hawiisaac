from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from applications.equipments.models import WorkoutType
from applications.session.models import SessionStatus


class SessionWorkoutInput(BaseModel):
    workout_id: int
    content_id: Optional[int] = None
    note: Optional[str] = None
    order: Optional[int] = Field(default=None, gt=0)


class WorkoutSessionCreate(BaseModel):
    date: date
    duration_minutes: int = Field(default=0, ge=0)
    note: Optional[str] = None
    user_weight_kg: Optional[float] = Field(default=None, gt=0)
    workouts: List[SessionWorkoutInput] = Field(min_length=1)


class SessionWorkoutCreate(BaseModel):
    session_id: int
    workout_id: int
    content_id: Optional[int] = None
    note: Optional[str] = None
    order: Optional[int] = Field(default=None, gt=0)


class SetLogCreate(BaseModel):
    session_workout_id: int
    weight: float = Field(ge=0)
    reps: int = Field(gt=0)
    order: int = Field(gt=0)
    duration_seconds: int = Field(default=0, ge=0)
    is_completed: bool = True


class CardioLogCreate(BaseModel):
    session_workout_id: int
    time_minutes: float = Field(gt=0)
    distance: float = Field(ge=0)
    speed: Optional[float] = Field(default=None, ge=0)
    incline: Optional[float] = Field(default=None, ge=0)
    user_weight_kg: Optional[float] = Field(default=None, gt=0)


class SessionWorkoutComplete(BaseModel):
    note: Optional[str] = None
    mark_session_complete_if_finished: bool = True


class SessionComplete(BaseModel):
    duration_minutes: Optional[int] = Field(default=None, ge=0)
    note: Optional[str] = None


class SetLogOut(BaseModel):
    id: int
    weight: float
    reps: int
    order: int
    duration_seconds: int
    is_completed: bool
    volume: float
    one_rm: float


class CardioLogOut(BaseModel):
    id: int
    time_minutes: float
    distance: float
    speed: Optional[float] = None
    incline: Optional[float] = None
    calories_burned: float
    user_weight_kg: Optional[float] = None


class SessionWorkoutOut(BaseModel):
    id: int
    order: int
    workout: dict
    content: Optional[dict] = None
    note: Optional[str] = None
    is_completed: bool
    estimated_calories_burned: float
    actual_calories_burned: float
    set_logs: List[SetLogOut]
    cardio_log: Optional[CardioLogOut] = None


class WorkoutSessionOut(BaseModel):
    id: int
    user_id: UUID
    date: date
    duration_minutes: int
    note: Optional[str] = None
    user_weight_kg: Optional[float] = None
    status: SessionStatus
    current_workout_order: int
    total_calories_burned: float
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    workouts: List[SessionWorkoutOut]


class StartContentLogOut(BaseModel):
    session: WorkoutSessionOut
    first_session_workout: SessionWorkoutOut


class StartWorkoutLogOut(BaseModel):
    session: WorkoutSessionOut
    first_session_workout: SessionWorkoutOut


class ActiveSessionOut(BaseModel):
    session: WorkoutSessionOut
    # current_session_workout: Optional[SessionWorkoutOut] = None


class ProgressSummaryOut(BaseModel):
    total_workouts: int
    total_sets: int
    total_volume: float
    avg_duration: float
    total_calories_burned: float


class ProgressChartPoint(BaseModel):
    date: date
    volume: float


class ProgressBestOut(BaseModel):
    workout_id: int
    workout_name: str
    equipment_name: Optional[str] = None
    date: date
    best_1rm: float
    previous_best_1rm: float
    improvement: float
