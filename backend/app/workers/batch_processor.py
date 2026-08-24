"""
Concurrent batch processor.
Processes many payments with controlled concurrency:
- asyncio.Semaphore for overall concurrency (default: 20)
- Separate LLM semaphore for rate-limiting (default: 5)
- Known failure codes skip LLM entirely → fast deterministic path
"""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

from app.agent.graph import get_recovery_graph
from app.agent.state import GraphState
from app.database import AsyncSessionLocal
from app.models.db_models import (
    Transaction, BatchRun, BatchStatus,
    PaymentStatus, FailureCode,
)
from app.config import get_settings

settings = get_settings()

# LLM-required codes (only UNKNOWN requires LLM; all others are deterministic)
LLM_REQUIRED_CODES = {FailureCode.UNKNOWN}


async def process_single_payment(
    payment_id: str,
    semaphore: asyncio.Semaphore,
    llm_semaphore: asyncio.Semaphore,
    failure_code: FailureCode,
) -> dict:
    """
    Run the recovery agent for a single payment.
    Uses separate semaphores for general vs LLM-heavy workloads.
    """
    # Use LLM semaphore for unknown codes (LLM will be called)
    needs_llm = failure_code in LLM_REQUIRED_CODES
    ctx_semaphore = llm_semaphore if needs_llm else semaphore

    async with ctx_semaphore:
        try:
            start_time = time.monotonic()
            graph = get_recovery_graph()
            initial_state = GraphState(
                payment_id=payment_id,
                customer_id="",  # loaded by ingest node
            )
            result = await graph.ainvoke(initial_state)
            elapsed_ms = (time.monotonic() - start_time) * 1000

            return {
                "payment_id": payment_id,
                "status": result["payment_status"].value,
                "amount_recovered": str(result.get("amount_recovered", Decimal("0"))),
                "failure_code": failure_code.value,
                "elapsed_ms": elapsed_ms,
                "error": None,
            }
        except Exception as exc:
            return {
                "payment_id": payment_id,
                "status": "ERROR",
                "amount_recovered": "0",
                "failure_code": failure_code.value,
                "elapsed_ms": 0,
                "error": str(exc)[:300],
            }


async def run_batch(
    batch_id: Optional[str] = None,
    payment_ids: Optional[List[str]] = None,
    concurrency: int | None = None,
    llm_concurrency: int | None = None,
) -> dict:
    """
    Process a batch of failed payments concurrently.

    Args:
        batch_id: Optional batch run ID to update.
        payment_ids: Specific payments to process. If None, processes all FAILED ones.
        concurrency: Max concurrent payments (default from settings).
        llm_concurrency: Max concurrent LLM calls (default from settings).
    """
    concurrency = concurrency or settings.batch_concurrency
    llm_concurrency = llm_concurrency or settings.llm_concurrency

    semaphore = asyncio.Semaphore(concurrency)
    llm_semaphore = asyncio.Semaphore(llm_concurrency)

    async with AsyncSessionLocal() as db:
        # Load payments to process
        if payment_ids:
            q = select(Transaction).where(Transaction.id.in_(payment_ids))
        else:
            q = select(Transaction).where(
                Transaction.status == PaymentStatus.FAILED
            )
        result = await db.execute(q)
        transactions = result.scalars().all()

    if not transactions:
        return {
            "batch_id": str(batch_id),
            "total": 0,
            "recovered": 0,
            "escalated": 0,
            "error": "No payments to process",
        }

    # Create / update batch run record
    batch_uuid = uuid.UUID(batch_id) if batch_id else uuid.uuid4()
    async with AsyncSessionLocal() as db:
        existing = await db.get(BatchRun, batch_uuid)
        if existing is None:
            batch_run = BatchRun(
                id=batch_uuid,
                started_at=datetime.utcnow(),
                total_payments=len(transactions),
                revenue_at_risk=sum(t.amount for t in transactions),
                status=BatchStatus.RUNNING,
            )
            db.add(batch_run)
        else:
            existing.status = BatchStatus.RUNNING
            existing.total_payments = len(transactions)
        await db.commit()

    # Build tasks
    tasks = [
        process_single_payment(
            payment_id=txn.id,
            semaphore=semaphore,
            llm_semaphore=llm_semaphore,
            failure_code=txn.failure_code,
        )
        for txn in transactions
    ]

    print(f"[batch] Processing {len(tasks)} payments (concurrency={concurrency}, llm={llm_concurrency})")
    start = time.monotonic()
    results = await asyncio.gather(*tasks, return_exceptions=False)
    elapsed = time.monotonic() - start

    # Aggregate results
    recovered = sum(1 for r in results if r["status"] == "RECOVERED")
    escalated = sum(1 for r in results if r["status"] == "ESCALATED")
    exhausted = sum(1 for r in results if r["status"] == "EXHAUSTED")
    human_review = sum(1 for r in results if r["status"] == "HUMAN_REVIEW")
    pending = sum(1 for r in results if r["status"] == "PENDING_RECOVERY")
    errors = sum(1 for r in results if r["status"] == "ERROR")

    revenue_recovered = sum(
        Decimal(r["amount_recovered"]) for r in results if r["status"] == "RECOVERED"
    )

    avg_ms = sum(r["elapsed_ms"] for r in results) / max(len(results), 1)

    print(f"[batch] Done in {elapsed:.1f}s | recovered={recovered} escalated={escalated} errors={errors}")
    print(f"[batch] Revenue recovered: ₹{revenue_recovered:,.2f} | avg latency: {avg_ms:.0f}ms")

    # Update batch run record
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(BatchRun)
            .where(BatchRun.id == batch_uuid)
            .values(
                completed_at=datetime.utcnow(),
                recovered=recovered,
                escalated=escalated,
                exhausted=exhausted,
                human_review=human_review,
                pending=pending,
                revenue_recovered=revenue_recovered,
                status=BatchStatus.COMPLETED,
            )
        )
        await db.commit()

    return {
        "batch_id": str(batch_uuid),
        "total": len(results),
        "recovered": recovered,
        "escalated": escalated,
        "exhausted": exhausted,
        "human_review": human_review,
        "pending": pending,
        "errors": errors,
        "revenue_recovered": str(revenue_recovered),
        "elapsed_seconds": round(elapsed, 2),
        "avg_latency_ms": round(avg_ms, 1),
        "throughput_per_sec": round(len(results) / elapsed, 1),
    }
