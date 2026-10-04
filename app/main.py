from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import time, date, timedelta
from app.core.config import get_settings
from app.db.session import engine, AsyncSessionLocal
from app.db.base import Base
from app.api.v1.api import api_router
from app.models.user import User
from app.models.factory import Factory
from app.models.machine import Machine
from app.models.tariff import Tariff
from app.models.report import Report
from app.models.optimization import OptimizationResult, OptimizationSummary
from app.core.security import get_password_hash
from app.services.optimizer import optimize_schedule, calculate_baseline_cost

settings = get_settings()

async def seed_data(db: AsyncSession):
    result = await db.execute(select(User).where(User.email == "tharuka@nookclothes.lk"))
    if result.scalar_one_or_none():
        return

    factory = Factory(
        name="Nook Clothes",
        code="NOOK-01",
        tariff_plan="CEB Industrial Tariff I-2 / I-3",
        start_time=time(7, 0),
        end_time=time(21, 0),
        working_days=26
    )
    db.add(factory)
    await db.flush()

    admin = User(
        name="Tharuka Thilakarathna",
        email="tharuka@nookclothes.lk",
        hashed_password=get_password_hash("energy@2024"),
        phone="0771234567",
        is_superuser=True,
        factory_id=factory.id
    )
    db.add(admin)

    machines_data = [
        {
            "name": "Fabric Cutter",
            "model_name": "Juki Cutter Pro X1",
            "category": "Cutting",
            "quantity": 2,
            "power_w": 4000.0,
            "required_hours": 3.0,
            "available_start": time(8, 0),
            "available_end": time(18, 0),
            "priority": "High",
            "color": "blue",
        },
        {
            "name": "Sewing Machine Line",
            "model_name": "Brother Industrial S-7200",
            "category": "Sewing",
            "quantity": 10,
            "power_w": 500.0,
            "required_hours": 8.0,
            "available_start": time(8, 0),
            "available_end": time(17, 0),
            "priority": "High",
            "color": "green",
        },
        {
            "name": "Overlock Machine",
            "model_name": "Pegasus M700",
            "category": "Finishing",
            "quantity": 4,
            "power_w": 750.0,
            "required_hours": 6.0,
            "available_start": time(8, 0),
            "available_end": time(18, 0),
            "priority": "Medium",
            "color": "amber",
        },
        {
            "name": "Steam Iron Station",
            "model_name": "Veit 8941",
            "category": "Finishing",
            "quantity": 3,
            "power_w": 2200.0,
            "required_hours": 4.0,
            "available_start": time(9, 0),
            "available_end": time(18, 0),
            "priority": "Medium",
            "color": "blue",
        },
        {
            "name": "Washing Unit",
            "model_name": "Tolkar Smartwash",
            "category": "Washing",
            "quantity": 1,
            "power_w": 5500.0,
            "required_hours": 2.0,
            "available_start": time(7, 0),
            "available_end": time(20, 0),
            "priority": "Low",
            "color": "green",
        },
    ]

    machine_objects = []
    for m in machines_data:
        machine = Machine(
            factory_id=factory.id,
            name=m["name"],
            model_name=m["model_name"],
            category=m["category"],
            quantity=m["quantity"],
            power_w=m["power_w"],
            required_hours=m["required_hours"],
            available_start=m["available_start"],
            available_end=m["available_end"],
            priority=m["priority"],
            color=m["color"],
        )
        db.add(machine)
        machine_objects.append(machine)

    await db.flush()

    tariffs = [
        Tariff(period="Off-Peak", start_time=time(22, 30), end_time=time(5, 30), rate_per_kwh=33.0),
        Tariff(period="Day", start_time=time(5, 30), end_time=time(18, 30), rate_per_kwh=47.0),
        Tariff(period="Peak", start_time=time(18, 30), end_time=time(22, 30), rate_per_kwh=106.0),
    ]
    db.add_all(tariffs)
    await db.flush()

    optimized = optimize_schedule(machine_objects, tariffs, factory.start_time, factory.end_time)
    current_cost = calculate_baseline_cost(machine_objects, tariffs, factory.start_time, factory.end_time)
    optimized_cost = round(sum(item["cost"] for item in optimized), 2)
    daily_saving = round(max(current_cost - optimized_cost, 0), 2)
    monthly_saving = round(daily_saving * factory.working_days, 2)
    saving_percentage = round((daily_saving / current_cost) * 100, 2) if current_cost > 0 else 0.0
    total_energy = round(sum(item["energy_kwh"] for item in optimized), 2)

    for item in optimized:
        db.add(OptimizationResult(
            factory_id=factory.id,
            machine_id=item["machine_id"],
            scheduled_start=item["scheduled_start"],
            scheduled_end=item["scheduled_end"],
            energy_kwh=item["energy_kwh"],
            cost=item["cost"],
        ))

    db.add(OptimizationSummary(
        factory_id=factory.id,
        current_cost=current_cost,
        optimized_cost=optimized_cost,
        daily_saving=daily_saving,
        monthly_saving=monthly_saving,
        saving_percentage=saving_percentage,
    ))

    today = date.today()
    for days_ago in range(7):
        factor = 1.0 + (days_ago % 3) * 0.01
        curr = round(current_cost * factor, 2)
        opt = round(optimized_cost * factor, 2)
        sav = round(curr - opt, 2)
        energy = round(total_energy * factor, 2)
        db.add(Report(
            factory_id=factory.id,
            report_date=today - timedelta(days=days_ago),
            current_cost=curr,
            optimized_cost=opt,
            saving=sav,
            energy_kwh=energy,
            saving_percentage=round((sav / curr) * 100, 2) if curr > 0 else 0.0,
        ))

    await db.commit()
    print("Seed data created successfully!")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        await seed_data(db)
    yield
    await engine.dispose()

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "Energy Optimization API is running"}
