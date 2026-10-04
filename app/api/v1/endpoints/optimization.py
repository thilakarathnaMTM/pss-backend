from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import date
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.factory import Factory
from app.models.machine import Machine
from app.models.tariff import Tariff
from app.models.optimization import OptimizationResult, OptimizationSummary
from app.models.report import Report
from app.services.optimizer import optimize_schedule, calculate_baseline_cost
from app.schemas.optimization import OptimizationResponse, ScheduleItem

router = APIRouter(prefix="/optimize", tags=["Optimization"])

@router.post("", response_model=OptimizationResponse)
async def run_optimization(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.factory_id:
        raise HTTPException(status_code=400, detail="No factory linked")

    factory_result = await db.execute(select(Factory).where(Factory.id == current_user.factory_id))
    factory = factory_result.scalar_one_or_none()
    if not factory:
        raise HTTPException(status_code=404, detail="Factory not found")

    machines_result = await db.execute(select(Machine).where(Machine.factory_id == factory.id))
    machines = machines_result.scalars().all()
    if not machines:
        raise HTTPException(status_code=400, detail="No machines found")

    tariffs_result = await db.execute(select(Tariff))
    tariffs = tariffs_result.scalars().all()
    if not tariffs:
        raise HTTPException(status_code=400, detail="No tariffs configured")

    optimized = optimize_schedule(machines, tariffs, factory.start_time, factory.end_time)
    current_cost = calculate_baseline_cost(machines, tariffs, factory.start_time, factory.end_time)
    optimized_cost = round(sum(item["cost"] for item in optimized), 2)
    daily_saving = round(max(current_cost - optimized_cost, 0), 2)
    monthly_saving = round(daily_saving * factory.working_days, 2)
    saving_percentage = round((daily_saving / current_cost) * 100, 2) if current_cost > 0 else 0.0
    total_energy = round(sum(item["energy_kwh"] for item in optimized), 2)

    await db.execute(delete(OptimizationResult).where(OptimizationResult.factory_id == factory.id))
    await db.execute(delete(OptimizationSummary).where(OptimizationSummary.factory_id == factory.id))

    schedules = []
    for item in optimized:
        result = OptimizationResult(
            factory_id=factory.id,
            machine_id=item["machine_id"],
            scheduled_start=item["scheduled_start"],
            scheduled_end=item["scheduled_end"],
            energy_kwh=item["energy_kwh"],
            cost=item["cost"]
        )
        db.add(result)

        schedules.append(ScheduleItem(
            machine_id=item["machine_id"],
            machine_name=item["machine_name"],
            category=next((m.category for m in machines if m.id == item["machine_id"]), "General"),
            scheduled_start=item["scheduled_start"],
            scheduled_end=item["scheduled_end"],
            energy_kwh=item["energy_kwh"],
            cost=item["cost"],
            total_power_kw=item["total_power_kw"],
            required_hours=item["required_hours"],
            saving=item.get("saving", 0)
        ))

    summary = OptimizationSummary(
        factory_id=factory.id,
        current_cost=current_cost,
        optimized_cost=optimized_cost,
        daily_saving=daily_saving,
        monthly_saving=monthly_saving,
        saving_percentage=saving_percentage
    )
    db.add(summary)

    today = date.today()
    existing_report = await db.execute(
        select(Report).where(Report.factory_id == factory.id, Report.report_date == today)
    )
    report = existing_report.scalar_one_or_none()
    if report:
        report.current_cost = current_cost
        report.optimized_cost = optimized_cost
        report.saving = daily_saving
        report.energy_kwh = total_energy
        report.saving_percentage = saving_percentage
    else:
        report = Report(
            factory_id=factory.id,
            report_date=today,
            current_cost=current_cost,
            optimized_cost=optimized_cost,
            saving=daily_saving,
            energy_kwh=total_energy,
            saving_percentage=saving_percentage
        )
        db.add(report)

    await db.commit()

    return OptimizationResponse(
        schedules=schedules,
        current_cost=current_cost,
        optimized_cost=optimized_cost,
        daily_saving=daily_saving,
        monthly_saving=monthly_saving,
        saving_percentage=saving_percentage,
        total_energy_kwh=total_energy
    )
