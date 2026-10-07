from datetime import date
from typing import Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.factory import Factory
from app.models.machine import Machine
from app.models.tariff import Tariff
from app.models.optimization import OptimizationResult, OptimizationSummary
from app.models.report import Report
from app.services.optimizer import optimize_schedule, calculate_baseline_cost


async def recalculate(db: AsyncSession, factory: Factory) -> dict:
    """Re-run the optimizer for a factory and replace its stored schedule, summary and today's report.

    Called after every machine / factory change so the stored result never goes stale.
    The caller commits. `error` is set when nothing could be scheduled (old results are cleared).
    """
    machines = (await db.execute(select(Machine).where(Machine.factory_id == factory.id))).scalars().all()
    tariffs = (await db.execute(select(Tariff))).scalars().all()

    await db.execute(delete(OptimizationResult).where(OptimizationResult.factory_id == factory.id))
    await db.execute(delete(OptimizationSummary).where(OptimizationSummary.factory_id == factory.id))

    out = {
        "machines": machines, "schedules": [], "skipped": [], "error": None,
        "current_cost": 0.0, "optimized_cost": 0.0, "daily_saving": 0.0,
        "monthly_saving": 0.0, "saving_percentage": 0.0, "total_energy": 0.0,
    }
    if not machines:
        out["error"] = "No machines found"
        return out
    if not tariffs:
        out["error"] = "No tariffs configured"
        return out

    optimized = optimize_schedule(machines, tariffs, factory.start_time, factory.end_time)
    if not optimized:
        out["error"] = (
            "No machine can be scheduled. Check that each machine's window fits its required hours inside factory hours."
        )
        out["skipped"] = [m.name for m in machines]
        return out

    current_cost = calculate_baseline_cost(machines, tariffs, factory.start_time, factory.end_time)
    optimized_cost = round(sum(i["cost"] for i in optimized), 2)
    daily_saving = round(max(current_cost - optimized_cost, 0), 2)
    saving_pct = round(daily_saving / current_cost * 100, 2) if current_cost > 0 else 0.0
    total_energy = round(sum(i["energy_kwh"] for i in optimized), 2)
    monthly_saving = round(daily_saving * factory.working_days, 2)

    for item in optimized:
        db.add(OptimizationResult(
            factory_id=factory.id, machine_id=item["machine_id"],
            scheduled_start=item["scheduled_start"], scheduled_end=item["scheduled_end"],
            energy_kwh=item["energy_kwh"], cost=item["cost"],
        ))
    db.add(OptimizationSummary(
        factory_id=factory.id, current_cost=current_cost, optimized_cost=optimized_cost,
        daily_saving=daily_saving, monthly_saving=monthly_saving, saving_percentage=saving_pct,
    ))

    today = date.today()
    report = (await db.execute(
        select(Report).where(Report.factory_id == factory.id, Report.report_date == today)
    )).scalar_one_or_none()
    if report is None:
        report = Report(factory_id=factory.id, report_date=today)
        db.add(report)
    report.current_cost = current_cost
    report.optimized_cost = optimized_cost
    report.saving = daily_saving
    report.energy_kwh = total_energy
    report.saving_percentage = saving_pct

    scheduled_ids = {i["machine_id"] for i in optimized}
    out.update(
        schedules=optimized, skipped=[m.name for m in machines if m.id not in scheduled_ids],
        current_cost=current_cost, optimized_cost=optimized_cost, daily_saving=daily_saving,
        monthly_saving=monthly_saving, saving_percentage=saving_pct, total_energy=total_energy,
    )
    return out


async def get_factory(db: AsyncSession, factory_id: Optional[int]) -> Optional[Factory]:
    if not factory_id:
        return None
    return (await db.execute(select(Factory).where(Factory.id == factory_id))).scalar_one_or_none()
