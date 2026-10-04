from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.factory import Factory
from app.models.machine import Machine
from app.models.optimization import OptimizationResult, OptimizationSummary
from app.schemas.dashboard import DashboardOut
from app.schemas.optimization import ScheduleItem

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("", response_model=DashboardOut)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.factory_id:
        raise HTTPException(status_code=400, detail="No factory linked")

    factory_result = await db.execute(select(Factory).where(Factory.id == current_user.factory_id))
    factory = factory_result.scalar_one_or_none()
    if not factory:
        raise HTTPException(status_code=404, detail="Factory not found")

    summary_result = await db.execute(
        select(OptimizationSummary)
        .where(OptimizationSummary.factory_id == factory.id)
        .order_by(OptimizationSummary.created_at.desc())
    )
    summary = summary_result.scalar_one_or_none()

    if not summary:
        return DashboardOut(
            factory_name=factory.name,
            factory_code=factory.code,
            current_daily_cost=0,
            optimized_daily_cost=0,
            daily_saving=0,
            monthly_saving=0,
            saving_percentage=0,
            total_energy_kwh=0,
            cost_per_unit=0,
            machines_optimized=0,
            schedules=[]
        )

    results = await db.execute(
        select(OptimizationResult).where(OptimizationResult.factory_id == factory.id)
    )
    opt_results = results.scalars().all()

    machines_result = await db.execute(select(Machine).where(Machine.factory_id == factory.id))
    machines = {m.id: m for m in machines_result.scalars().all()}

    schedules = []
    total_energy = 0.0
    for r in opt_results:
        m = machines.get(r.machine_id)
        power_kw = ((m.quantity * m.power_w) / 1000.0) if m else 0.0
        schedules.append(ScheduleItem(
            machine_id=r.machine_id,
            machine_name=m.name if m else "",
            category=m.category if m else "General",
            scheduled_start=r.scheduled_start,
            scheduled_end=r.scheduled_end,
            energy_kwh=r.energy_kwh,
            cost=r.cost,
            total_power_kw=round(power_kw, 3),
            required_hours=m.required_hours if m else 0,
            saving=0
        ))
        total_energy += r.energy_kwh

    cost_per_unit = round(summary.optimized_cost / total_energy, 2) if total_energy > 0 else 0

    return DashboardOut(
        factory_name=factory.name,
        factory_code=factory.code,
        current_daily_cost=summary.current_cost,
        optimized_daily_cost=summary.optimized_cost,
        daily_saving=summary.daily_saving,
        monthly_saving=summary.monthly_saving,
        saving_percentage=summary.saving_percentage,
        total_energy_kwh=round(total_energy, 2),
        cost_per_unit=cost_per_unit,
        machines_optimized=len(schedules),
        schedules=schedules
    )
