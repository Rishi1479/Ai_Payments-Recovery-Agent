"""Recovery run API router."""
import uuid
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.agent.graph import get_recovery_graph
from app.agent.state import GraphState
from app.models.db_models import Transaction, BatchRun
from app.models.schemas import (
    RecoveryRunRequest, RecoveryRunResponse, BatchRunRead, AuditEventRead
)
from app.workers.batch_processor import run_batch

router = APIRouter(prefix="/api/recovery", tags=["recovery"])


@router.post("/run", response_model=RecoveryRunResponse)
async def run_single_recovery(
    req: RecoveryRunRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run the recovery agent on a single payment."""
    graph = get_recovery_graph()
    initial = GraphState(payment_id=req.payment_id, customer_id="")
    result = await graph.ainvoke(initial)

    return RecoveryRunResponse(
        payment_id=req.payment_id,
        status=result["payment_status"],
        amount_recovered=result.get("amount_recovered", 0),
        action_taken=result.get("recommended_action"),
        reason=result.get("action_reason", ""),
        audit_events=[
            AuditEventRead(
                id=uuid.uuid4(),
                transaction_id=req.payment_id,
                event_type=ae.event_type,
                node=ae.node,
                reason=ae.reason,
                result=ae.result,
                event_metadata=ae.metadata,
                timestamp=ae.timestamp,
            )
            for ae in result.get("audit_events", [])
        ],
    )


@router.post("/batch/start")
async def start_batch(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger batch recovery for all FAILED payments (runs in background)."""
    batch_id = str(uuid.uuid4())
    background_tasks.add_task(run_batch, batch_id=batch_id)
    return {"batch_id": batch_id, "message": "Batch processing started"}


@router.get("/batch/{batch_id}", response_model=BatchRunRead)
async def get_batch_status(batch_id: str, db: AsyncSession = Depends(get_db)):
    batch = await db.get(BatchRun, uuid.UUID(batch_id))
    if batch is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Batch run not found")
    return BatchRunRead.model_validate(batch)
