import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.machine import Machine
from app.models.tariff import Tariff
from app.models.planning import MonthlyProfile, OptimizationRun
from app.schemas.planning import ProfileOut, ProfileUpdate, RunOut
from app.services.planning import compute_profile, default_profiles, working_days_in
from app.services.scheduler import get_factory

router = APIRouter(tags=["Planning"])


async def _factory_or_400(db: AsyncSession, user: User):
    factory = await get_factory(db, user.factory_id)
    if not factory:
        raise HTTPException(status_code=400, detail="No factory linked")
    return factory


async def _computed(db: AsyncSession, factory_id: int, profiles) -> List[ProfileOut]:
    machines = (await db.execute(select(Machine).where(Machine.factory_id == factory_id))).scalars().all()
    tariffs = (await db.execute(select(Tariff))).scalars().all()
    return [ProfileOut(**compute_profile(p, machines, tariffs)) for p in profiles]


@router.get("/planning/profiles", response_model=List[ProfileOut])
async def list_profiles(
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Monthly operating profiles with their projected bill / kWh / KPIs (computed live from current machines)."""
    factory = await _factory_or_400(db, current_user)
    base = select(MonthlyProfile).where(MonthlyProfile.factory_id == factory.id)
    if (await db.execute(base.limit(1))).scalar_one_or_none() is None:
        # First visit: start with seasonal defaults for last year and this year.
        from datetime import date
        this_year = date.today().year
        for y in (this_year - 1, this_year):
            db.add_all(default_profiles(factory, y))
        await db.commit()
    query = base.order_by(MonthlyProfile.year, MonthlyProfile.month)
    if year is not None:
        query = query.where(MonthlyProfile.year == year)
    profiles = (await db.execute(query)).scalars().all()
    return await _computed(db, factory.id, profiles)


@router.post("/planning/years/{year}", response_model=List[ProfileOut], status_code=status.HTTP_201_CREATED)
async def create_year(year: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Add a year. Copies season / hours / inactive machines from the previous year if it exists."""
    if not 2000 <= year <= 2100:
        raise HTTPException(status_code=422, detail="Year must be between 2000 and 2100")
    factory = await _factory_or_400(db, current_user)
    existing = (await db.execute(
        select(MonthlyProfile).where(MonthlyProfile.factory_id == factory.id, MonthlyProfile.year == year).limit(1)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"{year} already exists")

    previous = {p.month: p for p in (await db.execute(
        select(MonthlyProfile).where(MonthlyProfile.factory_id == factory.id, MonthlyProfile.year == year - 1)
    )).scalars().all()}
    new = default_profiles(factory, year)
    for p in new:
        prev = previous.get(p.month)
        if prev:
            p.season, p.start_time, p.end_time = prev.season, prev.start_time, prev.end_time
            p.inactive_machine_ids = prev.inactive_machine_ids
        p.working_days = working_days_in(year, p.month)
    db.add_all(new)
    await db.commit()
    return await _computed(db, factory.id, new)


@router.delete("/planning/years/{year}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_year(year: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    factory = await _factory_or_400(db, current_user)
    await db.execute(delete(MonthlyProfile).where(MonthlyProfile.factory_id == factory.id, MonthlyProfile.year == year))
    await db.commit()
    return None


@router.put("/planning/profiles/{profile_id}", response_model=ProfileOut)
async def update_profile(
    profile_id: int,
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    factory = await _factory_or_400(db, current_user)
    profile = (await db.execute(
        select(MonthlyProfile).where(MonthlyProfile.id == profile_id, MonthlyProfile.factory_id == factory.id)
    )).scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    changes = data.model_dump(exclude_unset=True)
    start = changes.get("start_time", profile.start_time)
    end = changes.get("end_time", profile.end_time)
    if end <= start:
        raise HTTPException(status_code=422, detail="End time must be after the start time")
    if "season" in changes and changes["season"] not in ("Peak", "Normal", "Low"):
        raise HTTPException(status_code=422, detail="Season must be Peak, Normal or Low")
    if "inactive_machine_ids" in changes:
        changes["inactive_machine_ids"] = ",".join(str(i) for i in sorted(set(changes["inactive_machine_ids"])))
    for field, value in changes.items():
        setattr(profile, field, value)
    await db.commit()
    return (await _computed(db, factory.id, [profile]))[0]


@router.get("/history", response_model=List[RunOut])
async def list_runs(
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Saved optimizer runs, newest first."""
    factory = await _factory_or_400(db, current_user)
    runs = (await db.execute(
        select(OptimizationRun).where(OptimizationRun.factory_id == factory.id)
        .order_by(OptimizationRun.created_at.desc(), OptimizationRun.id.desc()).limit(limit)
    )).scalars().all()
    return [
        RunOut(
            id=r.id, created_at=r.created_at, trigger=r.trigger,
            current_cost=r.current_cost, optimized_cost=r.optimized_cost, daily_saving=r.daily_saving,
            saving_percentage=r.saving_percentage, energy_kwh=r.energy_kwh, productive_hours=r.productive_hours,
            machines_scheduled=r.machines_scheduled,
            kwh_per_hour=round(r.energy_kwh / r.productive_hours, 2) if r.productive_hours else 0.0,
            cost_per_hour=round(r.optimized_cost / r.productive_hours, 2) if r.productive_hours else 0.0,
            schedules=json.loads(r.schedule_json or "[]"),
        )
        for r in runs
    ]
