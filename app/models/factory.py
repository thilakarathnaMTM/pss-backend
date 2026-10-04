from sqlalchemy import String, Time, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from datetime import time

class Factory(Base):
    __tablename__ = "factories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    code: Mapped[str] = mapped_column(String(50), unique=True)
    tariff_plan: Mapped[str] = mapped_column(String(100), default="CEB Industrial Tariff I-2 / I-3")
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    working_days: Mapped[int] = mapped_column(Integer, default=26)
    manager = relationship("User", back_populates="factory", uselist=False)
    machines = relationship("Machine", back_populates="factory", cascade="all, delete-orphan")