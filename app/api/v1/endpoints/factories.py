from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.factory import Factory
from app.services.scheduler import recalculate
from app.schemas.factory import FactoryOut, FactoryUpdate

router = APIRouter(prefix="/factories", tags=["Factories"])

@router.get("/me", response_model=FactoryOut)
async def get_my_factory(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not current_user.factory_id:
        raise HTTPException(status_code=404, detail="No factory linked")
    result = await db.execute(select(Factory).where(Factory.id == current_user.factory_id))
    factory = result.scalar_one_or_none()
    if not factory:
        raise HTTPException(status_code=404, detail="Factory not found")
    return factory

@router.put("/me", response_model=FactoryOut)
async def update_my_factory(
    data: FactoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.factory_id:
        raise HTTPException(status_code=404, detail="No factory linked")
    result = await db.execute(select(Factory).where(Factory.id == current_user.factory_id))
    factory = result.scalar_one_or_none()
    if not factory:
        raise HTTPException(status_code=404, detail="Factory not found")
    changes = data.model_dump(exclude_unset=True)
    start = changes.get("start_time", factory.start_time)
    end = changes.get("end_time", factory.end_time)
    if end <= start:
        raise HTTPException(status_code=422, detail="Factory end time must be after the start time")
    if not 1 <= changes.get("working_days", factory.working_days) <= 31:
        raise HTTPException(status_code=422, detail="Working days must be between 1 and 31")
    for field, value in changes.items():
        setattr(factory, field, value)
    await db.flush()
    await recalculate(db, factory)
    await db.commit()
    await db.refresh(factory)
    return factory