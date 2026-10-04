from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.report import Report
from app.schemas.report import ReportOut, ReportsSummary

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("", response_model=ReportsSummary)
async def get_reports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.factory_id:
        raise HTTPException(status_code=400, detail="No factory linked")

    result = await db.execute(
        select(Report)
        .where(Report.factory_id == current_user.factory_id)
        .order_by(Report.report_date.desc())
    )
    reports = result.scalars().all()

    if not reports:
        return ReportsSummary(
            avg_daily_saving=0,
            total_saving=0,
            avg_daily_energy=0,
            avg_current_cost=0,
            reports=[]
        )

    total_saving = sum(r.saving for r in reports)
    avg_daily_saving = round(total_saving / len(reports), 2)
    avg_daily_energy = round(sum(r.energy_kwh for r in reports) / len(reports), 2)
    avg_current_cost = round(sum(r.current_cost for r in reports) / len(reports), 2)

    return ReportsSummary(
        avg_daily_saving=avg_daily_saving,
        total_saving=round(total_saving, 2),
        avg_daily_energy=avg_daily_energy,
        avg_current_cost=avg_current_cost,
        reports=[ReportOut.model_validate(r) for r in reports]
    )