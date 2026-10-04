from pydantic import BaseModel
from datetime import time

class TariffOut(BaseModel):
    id: int
    period: str
    start_time: time
    end_time: time
    rate_per_kwh: float

    class Config:
        from_attributes = True