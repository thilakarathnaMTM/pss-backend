from pydantic import BaseModel
from typing import List
from app.schemas.optimization import ScheduleItem

class DashboardOut(BaseModel):
    factory_name: str
    factory_code: str
    current_daily_cost: float
    optimized_daily_cost: float
    daily_saving: float
    monthly_saving: float
    saving_percentage: float
    total_energy_kwh: float
    cost_per_unit: float
    productive_hours: float = 0
    kwh_per_productive_hour: float = 0
    cost_per_productive_hour: float = 0
    machines_optimized: int
    skipped_machines: List[str] = []
    schedules: List[ScheduleItem]