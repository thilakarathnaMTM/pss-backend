from fastapi import APIRouter
from app.api.v1.endpoints import auth, factories, machines, tariffs, optimization, dashboard, reports, planning

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(factories.router)
api_router.include_router(machines.router)
api_router.include_router(tariffs.router)
api_router.include_router(optimization.router)
api_router.include_router(dashboard.router)
api_router.include_router(reports.router)
api_router.include_router(planning.router)