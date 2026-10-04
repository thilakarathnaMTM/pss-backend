from sqlalchemy import String, Float, Time
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from datetime import time

class Tariff(Base):
    __tablename__ = "tariffs"
    id: Mapped[int] = mapped_column(primary_key=True)
    period: Mapped[str] = mapped_column(String(50))
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    rate_per_kwh: Mapped[float] = mapped_column(Float)