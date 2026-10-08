from pydantic import BaseModel, Field
from datetime import time, datetime
from typing import List, Optional


class ProfileOut(BaseModel):
    id: int
    year: int
    month: int
    season: str
    optimized: bool
    working_days: int
    start_time: time
    end_time: time
    inactive_machine_ids: List[int]
    hours_per_day: float
    active_machines: int
    skipped_machines: List[str]
    daily_kwh: float
    daily_cost: float
    monthly_kwh: float
    monthly_bill: float
    monthly_baseline: float
    monthly_saving: float
    potential_saving: float
    kwh_per_hour: float
    cost_per_hour: float


class ProfileUpdate(BaseModel):
    season: Optional[str] = None
    working_days: Optional[int] = Field(None, ge=0, le=31)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    inactive_machine_ids: Optional[List[int]] = None
    optimized: Optional[bool] = None


class RunScheduleItem(BaseModel):
    machine_name: str
    start: str
    end: str
    energy_kwh: float
    cost: float


class RunOut(BaseModel):
    id: int
    created_at: datetime
    trigger: str
    current_cost: float
    optimized_cost: float
    daily_saving: float
    saving_percentage: float
    energy_kwh: float
    productive_hours: float
    machines_scheduled: int
    kwh_per_hour: float
    cost_per_hour: float
    schedules: List[RunScheduleItem]
