from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    factory_id: Mapped[int | None] = mapped_column(ForeignKey("factories.id"), nullable=True)
    factory = relationship("Factory", back_populates="manager", uselist=False)