"""
Analytics service — all metrics are computed from the database.
LLM is not involved in any metric calculation.
"""
from __future__ import annotations

from decimal import Decimal
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from app.models.db_models import (
    Transaction, RecoveryActionRecord,
    PaymentStatus, FailureCode, RecoveryAction, ActionOutcome,
)
from app.models.schemas import (
    AnalyticsSummary, FailureTypeBreakdown, InterventionBreakdown, FunnelStep
)


async def get_summary(db: AsyncSession) -> AnalyticsSummary:
    """Calculate all top-level KPIs."""

    # Core counts and amounts
    result = await db.execute(
        select(
            func.count(Transaction.id).label("total"),
            func.sum(Transaction.revenue_at_risk).label("revenue_at_risk"),
            func.sum(Transaction.amount_recovered).label("revenue_recovered"),
            func.sum(case((Transaction.status == PaymentStatus.RECOVERED, 1), else_=0)).label("recovered"),
            func.sum(case((Transaction.status == PaymentStatus.ESCALATED, 1), else_=0)).label("escalated"),
            func.sum(case((Transaction.status == PaymentStatus.EXHAUSTED, 1), else_=0)).label("exhausted"),
            func.sum(case((Transaction.status == PaymentStatus.PENDING_RECOVERY, 1), else_=0)).label("pending"),
            func.sum(case((Transaction.status == PaymentStatus.HUMAN_REVIEW, 1), else_=0)).label("human_review"),
        )
    )
    row = result.one()

    total = row.total or 0
    revenue_at_risk = Decimal(str(row.revenue_at_risk or 0))
    revenue_recovered = Decimal(str(row.revenue_recovered or 0))
    recovered = row.recovered or 0
    escalated = row.escalated or 0
    exhausted = row.exhausted or 0
    pending = row.pending or 0
    human_review = row.human_review or 0

    recovery_rate = min(float(revenue_recovered / revenue_at_risk * 100), 100.0) if revenue_at_risk > 0 else 0.0

    # Retry success rate
    retry_result = await db.execute(
        select(
            func.count(RecoveryActionRecord.id).label("total_retries"),
            func.sum(case(
                (RecoveryActionRecord.outcome == ActionOutcome.SUCCESS, 1), else_=0
            )).label("successful_retries"),
        ).where(RecoveryActionRecord.action_type == RecoveryAction.RETRY)
    )
    retry_row = retry_result.one()
    total_retries = retry_row.total_retries or 0
    successful_retries = retry_row.successful_retries or 0
    retry_success_rate = (successful_retries / total_retries * 100) if total_retries > 0 else 0.0

    return AnalyticsSummary(
        total_revenue_at_risk=revenue_at_risk,
        total_revenue_recovered=revenue_recovered,
        recovery_rate=round(recovery_rate, 2),
        payments_processed=total,
        payments_recovered=recovered,
        payments_escalated=escalated,
        payments_exhausted=exhausted,
        payments_pending=pending,
        payments_human_review=human_review,
        retry_success_rate=round(retry_success_rate, 2),
        avg_processing_time_ms=0.0,  # populated by batch runner
    )


async def get_failure_type_breakdown(db: AsyncSession) -> List[FailureTypeBreakdown]:
    result = await db.execute(
        select(
            Transaction.failure_code,
            func.count(Transaction.id).label("total"),
            func.sum(case((Transaction.status == PaymentStatus.RECOVERED, 1), else_=0)).label("recovered"),
            func.sum(case((Transaction.status == PaymentStatus.ESCALATED, 1), else_=0)).label("escalated"),
            func.sum(Transaction.revenue_at_risk).label("revenue_at_risk"),
            func.sum(Transaction.amount_recovered).label("revenue_recovered"),
        ).group_by(Transaction.failure_code)
    )

    rows = result.all()
    breakdown = []
    for row in rows:
        at_risk = Decimal(str(row.revenue_at_risk or 0))
        recovered_amt = Decimal(str(row.revenue_recovered or 0))
        rate = min(float(recovered_amt / at_risk * 100), 100.0) if at_risk > 0 else 0.0
        breakdown.append(FailureTypeBreakdown(
            failure_code=row.failure_code.value,
            total=row.total,
            recovered=row.recovered or 0,
            escalated=row.escalated or 0,
            revenue_at_risk=at_risk,
            revenue_recovered=recovered_amt,
            recovery_rate=round(rate, 2),
        ))
    return breakdown


async def get_intervention_breakdown(db: AsyncSession) -> List[InterventionBreakdown]:
    result = await db.execute(
        select(
            RecoveryActionRecord.action_type,
            func.count(RecoveryActionRecord.id).label("total"),
            func.sum(case(
                (RecoveryActionRecord.outcome == ActionOutcome.SUCCESS, 1), else_=0
            )).label("successful"),
        ).group_by(RecoveryActionRecord.action_type)
    )

    rows = result.all()
    breakdown = []
    for row in rows:
        total = row.total or 0
        successful = row.successful or 0
        rate = (successful / total * 100) if total > 0 else 0.0

        # Get revenue recovered for this intervention type
        rev_result = await db.execute(
            select(func.sum(Transaction.amount_recovered))
            .join(RecoveryActionRecord, RecoveryActionRecord.transaction_id == Transaction.id)
            .where(RecoveryActionRecord.action_type == row.action_type)
            .where(Transaction.status == PaymentStatus.RECOVERED)
        )
        rev = Decimal(str(rev_result.scalar() or 0))

        breakdown.append(InterventionBreakdown(
            intervention=row.action_type.value,
            total_attempted=total,
            successful=successful,
            success_rate=round(rate, 2),
            revenue_recovered=rev,
        ))
    return breakdown


async def get_processing_funnel(db: AsyncSession) -> List[FunnelStep]:
    result = await db.execute(
        select(
            func.count(Transaction.id).label("total"),
            func.sum(Transaction.revenue_at_risk).label("total_risk"),
            func.sum(case((Transaction.status == PaymentStatus.RECOVERED, 1), else_=0)).label("recovered"),
            func.sum(case((Transaction.status == PaymentStatus.RECOVERED, Transaction.amount_recovered), else_=0)).label("recovered_amount"),
            func.sum(case((Transaction.status == PaymentStatus.ESCALATED, 1), else_=0)).label("escalated"),
            func.sum(case((Transaction.status == PaymentStatus.EXHAUSTED, 1), else_=0)).label("exhausted"),
            func.sum(case((Transaction.status == PaymentStatus.PENDING_RECOVERY, 1), else_=0)).label("pending"),
        )
    )
    row = result.one()
    total = row.total or 0
    processed = total - (row.pending or 0)

    return [
        FunnelStep(stage="Payments Failed", count=total, amount=Decimal(str(row.total_risk or 0))),
        FunnelStep(stage="Agent Processed", count=processed, amount=Decimal(str(row.total_risk or 0))),
        FunnelStep(stage="Recovery Attempted", count=(row.recovered or 0) + (row.exhausted or 0), amount=Decimal(str(row.total_risk or 0))),
        FunnelStep(stage="Successfully Recovered", count=row.recovered or 0, amount=Decimal(str(row.recovered_amount or 0))),
        FunnelStep(stage="Escalated", count=row.escalated or 0, amount=Decimal("0")),
    ]
