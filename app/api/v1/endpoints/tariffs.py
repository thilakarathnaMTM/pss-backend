from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.deps import get_db
from app.models.tariff import Tariff
from app.schemas.tariff import TariffOut

router = APIRouter(prefix="/tariffs", tags=["Tariffs"])

@router.get("", response_model=List[TariffOut])
async def list_tariffs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tariff).order_by(Tariff.id))
    return result.scalars().all()