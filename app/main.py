from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import select
from app.core.config import get_settings
from app.db.session import engine, AsyncSessionLocal
from app.db.base import Base
from app.api.v1.api import api_router
from app.models.user import User  # noqa: F401  (models are imported so their tables are registered)
from app.models.factory import Factory
from app.models.machine import Machine  # noqa: F401
from app.models.tariff import Tariff  # noqa: F401
from app.models.report import Report  # noqa: F401
from app.models.optimization import OptimizationResult, OptimizationSummary  # noqa: F401
from app.models.planning import MonthlyProfile, OptimizationRun  # noqa: F401
from app.services.scheduler import recalculate
from app.seed import seed_database, add_missing_columns

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(add_missing_columns)
    async with AsyncSessionLocal() as db:
        await seed_database(db)
    # Refresh every factory's stored schedule so nothing stale survives a restart.
    async with AsyncSessionLocal() as db:
        for factory in (await db.execute(select(Factory))).scalars().all():
            has_history = (await db.execute(
                select(OptimizationRun.id).where(OptimizationRun.factory_id == factory.id).limit(1)
            )).scalar_one_or_none()
            await recalculate(db, factory, trigger=None if has_history else "Initial calculation")
        await db.commit()
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
