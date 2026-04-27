from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WorkoutSessionCreate(BaseModel):
    date: date
    duration_minutes: int = Field(gt=0)


class WorkoutLogCreate(BaseModel):
    session_id: int
    workout_id: int
    note: Optional[str] = None


class SetLogCreate(BaseModel):
    workout_log_id: int
    weight: float = Field(ge=0)
    reps: int = Field(gt=0)
    order: int = Field(gt=0)
    is_completed: bool = True


class CardioLogCreate(BaseModel):
    workout_log_id: int
    time_minutes: float = Field(gt=0)
    distance: float = Field(ge=0)
    speed: Optional[float] = Field(default=None, ge=0)
    incline: Optional[float] = None


class SetLogOut(BaseModel):
    id: int
    weight: float
    reps: int
    order: int
    is_completed: bool
    volume: float
    one_rm: float


class CardioLogOut(BaseModel):
    id: int
    time_minutes: float
    distance: float
    speed: Optional[float] = None
    incline: Optional[float] = None


class WorkoutLogOut(BaseModel):
    id: int
    workout: dict
    note: Optional[str] = None
    set_logs: List[SetLogOut]
    cardio_log: Optional[CardioLogOut] = None


class WorkoutSessionOut(BaseModel):
    id: int
    user_id: UUID
    date: date
    duration_minutes: int
    created_at: str
    workout_logs: List[WorkoutLogOut]


class StartContentLogOut(BaseModel):
    session: WorkoutSessionOut
    first_workout_log: WorkoutLogOut


class StartWorkoutLogOut(BaseModel):
    session: WorkoutSessionOut
    first_workout_log: WorkoutLogOut


class ProgressSummaryOut(BaseModel):
    total_workouts: int
    total_sets: int
    total_volume: float
    avg_duration: float


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
