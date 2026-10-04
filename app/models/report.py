from sqlalchemy import Float, Integer, String, ForeignKey, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from datetime import date, datetime

class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    factory_id: Mapped[int] = mapped_column(ForeignKey("factories.id"))
    report_date: Mapped[date] = mapped_column(Date)
    current_cost: Mapped[float] = mapped_column(Float)
    optimized_cost: Mapped[float] = mapped_column(Float)
    saving: Mapped[float] = mapped_column(Float)
    energy_kwh: Mapped[float] = mapped_column(Float)
    saving_percentage: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)