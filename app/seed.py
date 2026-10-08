"""Demo seed data for a fresh database (also used to build the frontend's public/dummy.json).

Story: Nook Clothes ran its machines on habit in 2025 (cutting, ironing, washing, drying, packing and the
compressor pile up in the evening around dispatch, inside the CEB peak). They started using this app in
January 2026 and widened machine windows step by step, so the optimizer could move load out of the peak.

Reset a database to this seed (backs up the old file first):  python -m app.seed --reset
"""
import asyncio
import json
import shutil
import sys
from datetime import time, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import select, inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.factory import Factory
from app.models.machine import Machine
from app.models.tariff import Tariff
from app.models.report import Report
from app.models.planning import MonthlyProfile, OptimizationRun
from app.core.security import get_password_hash
from app.services.optimizer import optimize_schedule, calculate_baseline_cost
from app.services.planning import default_profiles, productive_hours

ADMIN = dict(name="Tharuka Thilakarathna", email="tharuka@nookclothes.lk", password="energy@2024", phone="0771234567")
FACTORY = dict(name="Nook Clothes", code="NOOK-01", tariff_plan="CEB Industrial Tariff I-2 / I-3",
               start_time=time(7, 0), end_time=time(23, 30), working_days=26)
TARIFFS = [
    dict(period="Off-Peak", start_time=time(22, 30), end_time=time(5, 30), rate_per_kwh=33.0),
    dict(period="Day", start_time=time(5, 30), end_time=time(18, 30), rate_per_kwh=47.0),
    dict(period="Peak", start_time=time(18, 30), end_time=time(22, 30), rate_per_kwh=106.0),
]

# usual_start = how the factory ran the machine before using the app (the cost baseline).
# manufactured_year drives the ageing estimate on the Machines page (older = more efficiency loss).
MACHINES = [
    dict(name="Fabric Cutter", model_name="Juki Cutter Pro X1", category="Cutting", quantity=2, power_w=4000.0,
         required_hours=3.0, available_start=time(7, 0), available_end=time(22, 0), usual_start=time(16, 30), manufactured_year=2019, priority="High", color="blue"),
    dict(name="Sewing Machine Line", model_name="Brother Industrial S-7200", category="Sewing", quantity=10, power_w=500.0,
         required_hours=8.0, available_start=time(8, 0), available_end=time(17, 0), usual_start=time(8, 0), manufactured_year=2016, priority="High", color="green"),
    dict(name="Overlock Machine", model_name="Pegasus M700", category="Sewing", quantity=4, power_w=750.0,
         required_hours=6.0, available_start=time(8, 0), available_end=time(22, 0), usual_start=time(13, 30), manufactured_year=2021, priority="Medium", color="amber"),
    dict(name="Steam Iron Station", model_name="Veit 8941", category="Finishing", quantity=3, power_w=2200.0,
         required_hours=4.0, available_start=time(8, 0), available_end=time(22, 0), usual_start=time(16, 0), manufactured_year=2014, priority="Medium", color="blue"),
    dict(name="Washing Unit", model_name="Tolkar Smartwash", category="Washing", quantity=1, power_w=5500.0,
         required_hours=2.0, available_start=time(7, 0), available_end=time(23, 30), usual_start=time(19, 0), manufactured_year=2018, priority="Low", color="green"),
    dict(name="Tumble Dryer", model_name="Electrolux T5550", category="Washing", quantity=1, power_w=6000.0,
         required_hours=2.0, available_start=time(7, 0), available_end=time(23, 30), usual_start=time(21, 0), manufactured_year=2015, priority="Low", color="amber"),
    dict(name="Fusing Press", model_name="Hashima HP-450", category="Finishing", quantity=2, power_w=3500.0,
         required_hours=3.0, available_start=time(8, 0), available_end=time(22, 0), usual_start=time(16, 0), manufactured_year=2022, priority="Medium", color="blue"),
    dict(name="Embroidery Machine", model_name="Tajima TMBR-SC", category="Embroidery", quantity=2, power_w=1200.0,
         required_hours=6.0, available_start=time(8, 0), available_end=time(23, 0), usual_start=time(14, 0), manufactured_year=2023, priority="Medium", color="green"),
    dict(name="Air Compressor", model_name="Atlas Copco GA11", category="Utilities", quantity=1, power_w=11000.0,
         required_hours=4.0, available_start=time(7, 0), available_end=time(23, 30), usual_start=time(15, 0), manufactured_year=2012, priority="High", color="amber"),
    dict(name="Packaging Sealer", model_name="Hualian FR-900", category="Packaging", quantity=2, power_w=1500.0,
         required_hours=2.0, available_start=time(8, 0), available_end=time(22, 0), usual_start=time(20, 0), manufactured_year=2020, priority="Low", color="blue"),
]

# Order in which the factory widened machine windows after adopting the app (history runs).
OPENED = [
    (datetime(2026, 1, 12, 10, 5), "Washing Unit"),
    (datetime(2026, 1, 26, 9, 40), "Air Compressor"),
    (datetime(2026, 2, 9, 11, 15), "Steam Iron Station"),
    (datetime(2026, 3, 2, 14, 20), "Packaging Sealer"),
    (datetime(2026, 3, 16, 9, 55), "Fabric Cutter"),
    (datetime(2026, 4, 6, 10, 30), "Fusing Press"),
    (datetime(2026, 5, 4, 15, 10), "Embroidery Machine"),
    (datetime(2026, 6, 1, 8, 45), "Tumble Dryer"),
    (datetime(2026, 6, 2, 9, 5), "Overlock Machine"),
]
ADOPTED = datetime(2026, 1, 5, 9, 12)
EXTRA_RERUNS = [datetime(2026, 8, 3, 9, 30), datetime(2026, 10, 5, 8, 50)]
PLAN_YEARS = {2025: False, 2026: True}  # year -> optimizer in use
REPORT_DAYS = 60  # working days of daily reports before today
# Daily production load varies a little (orders, absenteeism); costs and kWh scale with it.
LOAD = [1.00, 0.97, 1.03, 0.95, 1.02, 0.91, 1.04, 0.98, 1.01, 0.94, 1.05, 0.96, 1.00, 0.99, 1.02, 0.93]


def _minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def machine_objects(ids=True):
    """Seed machines as plain objects (id 1..N) for calculations outside the database."""
    return [SimpleNamespace(id=i + 1 if ids else None, **m) for i, m in enumerate(MACHINES)]


def tariff_objects():
    return [SimpleNamespace(id=i + 1, **t) for i, t in enumerate(TARIFFS)]


def state_at(opened_names):
    """Machines as configured at a point in history: machines not yet 'opened' still have the narrow
    habit window (usual start .. usual start + runtime + 1 h), so the optimizer could barely move them."""
    out = []
    for m in machine_objects():
        if m.name not in opened_names and _minutes(m.usual_start) > _minutes(m.available_start):
            s = _minutes(m.usual_start)
            e = min(s + int(m.required_hours * 60) + 60, _minutes(m.available_end))
            m = SimpleNamespace(**{**vars(m), "available_start": m.usual_start, "available_end": time(e // 60, e % 60)})
        out.append(m)
    return out


def run_summary(machines, tariffs, f_start, f_end):
    res = optimize_schedule(machines, tariffs, f_start, f_end)
    cur = calculate_baseline_cost(machines, tariffs, f_start, f_end)
    opt = round(sum(r["cost"] for r in res), 2)
    kwh = round(sum(r["energy_kwh"] for r in res), 2)
    hours = round(productive_hours(f_start, f_end), 2)
    return dict(
        current_cost=cur, optimized_cost=opt, daily_saving=round(max(cur - opt, 0), 2),
        saving_percentage=round((cur - opt) / cur * 100, 2) if cur else 0.0, energy_kwh=kwh,
        productive_hours=hours, machines_scheduled=len(res),
        schedules=[{"machine_name": r["machine_name"], "start": r["scheduled_start"].strftime("%H:%M"),
                    "end": r["scheduled_end"].strftime("%H:%M"), "energy_kwh": r["energy_kwh"], "cost": r["cost"]} for r in res],
    )


def history_runs():
    """(when, trigger, summary) for each saved run, oldest first."""
    tariffs, fs, fe = tariff_objects(), FACTORY["start_time"], FACTORY["end_time"]
    runs = [(ADOPTED, "Initial calculation", run_summary(state_at(set()), tariffs, fs, fe))]
    opened = set()
    for when, name in OPENED:
        opened.add(name)
        runs.append((when, f"Machine updated: {name}", run_summary(state_at(opened), tariffs, fs, fe)))
    final = run_summary(machine_objects(), tariffs, fs, fe)
    runs += [(when, "Manual re-run", final) for when in EXTRA_RERUNS]
    return runs


def daily_reports(today: date):
    """REPORT_DAYS working days (Mon-Sat) before today, using the current (fully optimized) setup."""
    base = run_summary(machine_objects(), tariff_objects(), FACTORY["start_time"], FACTORY["end_time"])
    rows, d, i = [], today - timedelta(days=1), 0
    while len(rows) < REPORT_DAYS:
        if d.weekday() != 6:
            f = LOAD[i % len(LOAD)]
            i += 1
            cur, opt = round(base["current_cost"] * f, 2), round(base["optimized_cost"] * f, 2)
            rows.append(dict(report_date=d, current_cost=cur, optimized_cost=opt, saving=round(cur - opt, 2),
                             energy_kwh=round(base["energy_kwh"] * f, 2),
                             saving_percentage=round((cur - opt) / cur * 100, 2) if cur else 0.0))
        d -= timedelta(days=1)
    return rows


async def seed_database(db: AsyncSession) -> bool:
    """Create the demo factory if the admin user does not exist yet. Returns True if it seeded."""
    if (await db.execute(select(User).where(User.email == ADMIN["email"]))).scalar_one_or_none():
        return False

    factory = Factory(**FACTORY)
    db.add(factory)
    await db.flush()
    db.add(User(name=ADMIN["name"], email=ADMIN["email"], hashed_password=get_password_hash(ADMIN["password"]),
                phone=ADMIN["phone"], is_superuser=True, factory_id=factory.id))
    for m in MACHINES:
        db.add(Machine(factory_id=factory.id, **m))
    if not (await db.execute(select(Tariff).limit(1))).scalar_one_or_none():
        db.add_all([Tariff(**t) for t in TARIFFS])

    for year, used in PLAN_YEARS.items():
        for p in default_profiles(factory, year):
            p.optimized = used
            db.add(p)

    for when, trigger, s in history_runs():
        db.add(OptimizationRun(
            factory_id=factory.id, created_at=when, trigger=trigger,
            current_cost=s["current_cost"], optimized_cost=s["optimized_cost"], daily_saving=s["daily_saving"],
            saving_percentage=s["saving_percentage"], energy_kwh=s["energy_kwh"],
            productive_hours=s["productive_hours"], machines_scheduled=s["machines_scheduled"],
            schedule_json=json.dumps(s["schedules"]),
        ))
    for r in daily_reports(date.today()):
        db.add(Report(factory_id=factory.id, **r))
    await db.commit()
    print("Seed data created successfully!")
    return True


def add_missing_columns(sync_conn) -> None:
    """Tiny migration for databases created before these columns existed (SQLite ALTER TABLE ADD COLUMN)."""
    insp = inspect(sync_conn)
    tables = insp.get_table_names()
    for table, column, ddl in [
        ("machines", "usual_start", "TIME"),
        ("machines", "manufactured_year", "INTEGER"),
        ("monthly_profiles", "optimized", "BOOLEAN NOT NULL DEFAULT 1"),
    ]:
        if table in tables and column not in {c["name"] for c in insp.get_columns(table)}:
            sync_conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
            if column == "optimized":  # past years were before the app was in use
                sync_conn.exec_driver_sql(f"UPDATE monthly_profiles SET optimized = (year >= {date.today().year})")


async def _reset() -> None:
    from app.core.config import get_settings
    from app.db.session import engine, AsyncSessionLocal
    from app.db.base import Base
    import app.main  # noqa: F401  registers every model
    from app.services.scheduler import recalculate

    url = get_settings().DATABASE_URL
    if url.startswith("sqlite"):
        path = Path(url.split("///", 1)[1])
        if path.exists():
            backup = path.with_name(f"{path.stem}.backup-{datetime.now():%Y%m%d-%H%M%S}{path.suffix}")
            shutil.move(path, backup)
            print(f"Old database moved to {backup}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        await seed_database(db)
    async with AsyncSessionLocal() as db:
        for factory in (await db.execute(select(Factory))).scalars().all():
            await recalculate(db, factory)
        await db.commit()
    await engine.dispose()


if __name__ == "__main__":
    if "--reset" in sys.argv:
        asyncio.run(_reset())
    else:
        print(__doc__)
