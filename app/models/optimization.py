from sqlalchemy import Float, Integer, Time, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from datetime import time, datetime

class OptimizationResult(Base):
    __tablename__ = "optimization_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    factory_id: Mapped[int] = mapped_column(ForeignKey("factories.id"))
    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"))
    scheduled_start: Mapped[time] = mapped_column(Time)
    scheduled_end: Mapped[time] = mapped_column(Time)
    energy_kwh: Mapped[float] = mapped_column(Float)
    cost: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class OptimizationSummary(Base):
    __tablename__ = "optimization_summaries"
    id: Mapped[int] = mapped_column(primary_key=True)
    factory_id: Mapped[int] = mapped_column(ForeignKey("factories.id"))
    current_cost: Mapped[float] = mapped_column(Float)
    optimized_cost: Mapped[float] = mapped_column(Float)
    daily_saving: Mapped[float] = mapped_column(Float)
    monthly_saving: Mapped[float] = mapped_column(Float)
    saving_percentage: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)