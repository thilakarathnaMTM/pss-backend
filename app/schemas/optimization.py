from pydantic import BaseModel
from datetime import time
from typing import List

class ScheduleItem(BaseModel):
    machine_id: int
    machine_name: str
    category: str
    scheduled_start: time
    scheduled_end: time
    energy_kwh: float
    cost: float
    total_power_kw: float
    required_hours: float
    saving: float = 0

class OptimizationResponse(BaseModel):
    schedules: List[ScheduleItem]
    current_cost: float
    optimized_cost: float
    daily_saving: float
    monthly_saving: float
    saving_percentage: float
    total_energy_kwh: float
    skipped_machines: List[str] = []