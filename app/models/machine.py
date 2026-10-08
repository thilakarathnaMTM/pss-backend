from sqlalchemy import String, Float, Integer, Time, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from datetime import time
from typing import Optional

class Machine(Base):
    __tablename__ = "machines"
    id: Mapped[int] = mapped_column(primary_key=True)
    factory_id: Mapped[int] = mapped_column(ForeignKey("factories.id"))
    name: Mapped[str] = mapped_column(String(100))
    model_name: Mapped[str] = mapped_column(String(100), default="")
    category: Mapped[str] = mapped_column(String(50), default="General")
    quantity: Mapped[int] = mapped_column(Integer)
    power_w: Mapped[float] = mapped_column(Float)
    required_hours: Mapped[float] = mapped_column(Float)
    available_start: Mapped[time] = mapped_column(Time)
    available_end: Mapped[time] = mapped_column(Time)
    # How the factory ran this machine before optimization. Used as the cost baseline; None = window open.
    usual_start: Mapped[Optional[time]] = mapped_column(Time, nullable=True, default=None)
    # Year the machine was built; used for the ageing / efficiency-loss estimate (None for older records).
    manufactured_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    color: Mapped[str] = mapped_column(String(20), default="blue")
    factory = relationship("Factory", back_populates="machines")
