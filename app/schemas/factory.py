from pydantic import BaseModel
from datetime import time
from typing import Optional

class FactoryCreate(BaseModel):
    name: str
    code: str
    tariff_plan: str = "CEB Industrial Tariff I-2 / I-3"
    start_time: time
    end_time: time
    working_days: int = 26

class FactoryUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    tariff_plan: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    working_days: Optional[int] = None

class FactoryOut(BaseModel):
    id: int
    name: str
    code: str
    tariff_plan: str
    start_time: time
    end_time: time
    working_days: int

    class Config:
        from_attributes = True