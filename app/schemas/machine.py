from pydantic import BaseModel, Field
from datetime import time
from typing import Optional

class MachineCreate(BaseModel):
    name: str
    model_name: str = ""
    category: str = "General"
    quantity: int = Field(gt=0)
    power_w: float = Field(gt=0)
    required_hours: float = Field(gt=0)
    available_start: time
    available_end: time
    priority: str = "Medium"
    color: str = "blue"

class MachineUpdate(BaseModel):
    name: Optional[str] = None
    model_name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[int] = Field(None, gt=0)
    power_w: Optional[float] = Field(None, gt=0)
    required_hours: Optional[float] = Field(None, gt=0)
    available_start: Optional[time] = None
    available_end: Optional[time] = None
    priority: Optional[str] = None
    color: Optional[str] = None

class MachineOut(BaseModel):
    id: int
    factory_id: int
    name: str
    model_name: str
    category: str
    quantity: int
    power_w: float
    required_hours: float
    available_start: time
    available_end: time
    priority: str
    color: str
    total_power_w: float = 0

    class Config:
        from_attributes = True
