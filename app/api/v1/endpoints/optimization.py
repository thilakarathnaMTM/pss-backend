from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.optimization import OptimizationResponse, ScheduleItem
from app.services.scheduler import recalculate, get_factory

router = APIRouter(prefix="/optimize", tags=["Optimization"])

@router.post("", response_model=OptimizationResponse)
async def run_optimization(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    factory = await get_factory(db, current_user.factory_id)
    if not factory:
        raise HTTPException(status_code=400, detail="No factory linked")

    result = await recalculate(db, factory, trigger="Manual re-run")
    if result["error"]:
        await db.commit()  # keeps the cleared (empty) result so nothing stale is shown
        raise HTTPException(status_code=400, detail=result["error"])
    await db.commit()

    categories = {m.id: m.category for m in result["machines"]}
    schedules = [
        ScheduleItem(
            machine_id=i["machine_id"], machine_name=i["machine_name"],
            category=categories.get(i["machine_id"], "General"),
            scheduled_start=i["scheduled_start"], scheduled_end=i["scheduled_end"],
            energy_kwh=i["energy_kwh"], cost=i["cost"], total_power_kw=i["total_power_kw"],
            required_hours=i["required_hours"], saving=i["saving"],
        )
        for i in result["schedules"]
    ]
    return OptimizationResponse(
        schedules=schedules,
        current_cost=result["current_cost"],
        optimized_cost=result["optimized_cost"],
        daily_saving=result["daily_saving"],
        monthly_saving=result["monthly_saving"],
        saving_percentage=result["saving_percentage"],
        total_energy_kwh=result["total_energy"],
        skipped_machines=result["skipped"],
    )
