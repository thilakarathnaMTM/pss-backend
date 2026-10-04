from pydantic import BaseModel
from datetime import date
from typing import List

class ReportOut(BaseModel):
    id: int
    report_date: date
    current_cost: float
    optimized_cost: float
    saving: float
    energy_kwh: float
    saving_percentage: float

    class Config:
        from_attributes = True

class ReportsSummary(BaseModel):
    avg_daily_saving: float
    total_saving: float
    avg_daily_energy: float
    avg_current_cost: float
    reports: List[ReportOut]