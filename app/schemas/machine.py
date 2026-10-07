from pydantic import BaseModel, Field, model_validator
from datetime import time
from typing import Optional

def check_window(start: time, end: time, hours: float) -> None:
    """Raise ValueError if the window is empty, overnight, or shorter than the required runtime."""
    s = start.hour * 60 + start.minute
    e = end.hour * 60 + end.minute
    if e <= s:
        raise ValueError("Available end time must be after the start time (overnight windows are not supported)")
    if hours * 60 > e - s:
        raise ValueError(f"Required runtime ({hours} h) is longer than the available window ({(e - s) / 60:.1f} h)")

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

    @model_validator(mode="after")
    def _window_ok(self):
        check_window(self.available_start, self.available_end, self.required_hours)
        return self

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
