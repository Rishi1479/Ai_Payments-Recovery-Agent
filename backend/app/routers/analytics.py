"""Analytics API router."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.db_models import Transaction, PaymentStatus
from app.services.analytics import (
    get_summary, get_failure_type_breakdown,
    get_intervention_breakdown, get_processing_funnel,
)
from app.models.schemas import (
    AnalyticsSummary, FailureTypeBreakdown,
    InterventionBreakdown, FunnelStep,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class DailyTrendItem(BaseModel):
    date: str
    failed: int
    recovered: int
    revenue_at_risk: float
    revenue_recovered: float


@router.get("/summary", response_model=AnalyticsSummary)
async def analytics_summary(db: AsyncSession = Depends(get_db)):
    return await get_summary(db)


@router.get("/by-failure-type", response_model=List[FailureTypeBreakdown])
@router.get("/failure-types", response_model=List[FailureTypeBreakdown])
async def by_failure_type(db: AsyncSession = Depends(get_db)):
    return await get_failure_type_breakdown(db)


@router.get("/by-intervention", response_model=List[InterventionBreakdown])
async def by_intervention(db: AsyncSession = Depends(get_db)):
    return await get_intervention_breakdown(db)


@router.get("/funnel", response_model=List[FunnelStep])
async def funnel(db: AsyncSession = Depends(get_db)):
    return await get_processing_funnel(db)


@router.get("/daily-trend", response_model=List[DailyTrendItem])
async def daily_trend(days: int = Query(14, ge=1, le=90), db: AsyncSession = Depends(get_db)):
    """Return daily trend metrics computed from live database transactions."""
    now = datetime.now(timezone.utc)
    trends = []
    
    # Query transactions from the database
    res = await db.execute(select(Transaction))
    txns = res.scalars().all()
    
    for i in range(days - 1, -1, -1):
        day_date = (now - timedelta(days=i)).strftime("%b %d")
        day_txns = [t for t in txns if t.created_at and t.created_at.strftime("%b %d") == day_date]
        
        failed = len(day_txns)
        recovered = len([t for t in day_txns if t.status == PaymentStatus.RECOVERED])
        at_risk = sum(float(t.revenue_at_risk or 0) for t in day_txns)
        rec_amt = sum(float(t.amount_recovered or 0) for t in day_txns)
        
        trends.append(
            DailyTrendItem(
                date=day_date,
                failed=failed,
                recovered=recovered,
                revenue_at_risk=at_risk,
                revenue_recovered=rec_amt,
            )
        )
    return trends
