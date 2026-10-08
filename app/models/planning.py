from sqlalchemy import String, Integer, Float, Time, ForeignKey, DateTime, Text, UniqueConstraint, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from datetime import time, datetime


class MonthlyProfile(Base):
    """Operating plan for one month of one year: season, working days, operating hours, inactive machines."""
    __tablename__ = "monthly_profiles"
    __table_args__ = (UniqueConstraint("factory_id", "year", "month", name="uq_profile_month"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    factory_id: Mapped[int] = mapped_column(ForeignKey("factories.id"))
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)  # 1-12
    season: Mapped[str] = mapped_column(String(20), default="Normal")
    working_days: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    # Stored as "inactive" so machines added later are active by default. Comma-separated machine ids.
    inactive_machine_ids: Mapped[str] = mapped_column(String(500), default="")
    # False = a month before the factory used this app: its bill is the usual (un-optimized) schedule.
    optimized: Mapped[bool] = mapped_column(Boolean, default=True)


class OptimizationRun(Base):
    """One saved optimizer run (history). Written on every manual re-run and every machine / factory change."""
    __tablename__ = "optimization_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    factory_id: Mapped[int] = mapped_column(ForeignKey("factories.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    trigger: Mapped[str] = mapped_column(String(150))
    current_cost: Mapped[float] = mapped_column(Float)
    optimized_cost: Mapped[float] = mapped_column(Float)
    daily_saving: Mapped[float] = mapped_column(Float)
    saving_percentage: Mapped[float] = mapped_column(Float)
    energy_kwh: Mapped[float] = mapped_column(Float)
    productive_hours: Mapped[float] = mapped_column(Float)
    machines_scheduled: Mapped[int] = mapped_column(Integer)
    schedule_json: Mapped[str] = mapped_column(Text, default="[]")
