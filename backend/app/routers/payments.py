"""Payments API router."""
import uuid
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.db_models import Transaction, AuditEvent, Classification, RecoveryActionRecord, PaymentStatus, FailureCode
from app.models.schemas import TransactionRead, TransactionListResponse, PaymentDetailResponse, AuditEventRead, RecoveryActionRead, CustomerRead, ClassificationOutput

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("/seed")
async def seed_data(count: int = Query(50, ge=1, le=500), db: AsyncSession = Depends(get_db)):
    """Seed the database with sample customers and failed payments."""
    from app.services.seed import seed_database
    added = await seed_database(db, count=count)
    return {"message": f"Successfully seeded {added} failed payment records", "count": added}


class PaymentInjectRequest(BaseModel):
    amount: Decimal = Decimal("4999.00")
    failure_code: FailureCode = FailureCode.BANK_TIMEOUT
    customer_email: Optional[str] = "customer@example.com"


@router.post("/inject", response_model=TransactionRead)
async def inject_payment(
    req: PaymentInjectRequest,
    db: AsyncSession = Depends(get_db),
):
    """Inject a single synthetic failed payment into the database."""
    import random
    from datetime import datetime, timezone
    from app.models.db_models import Customer, CustomerSegment

    email = req.customer_email or "customer@example.com"
    result = await db.execute(select(Customer).where(Customer.email == email))
    customer = result.scalar_one_or_none()

    if not customer:
        customer = Customer(
            id=uuid.uuid4(),
            name=email.split("@")[0].replace(".", " ").title(),
            email=email,
            segment=CustomerSegment.REGULAR,
            previous_successful_payments=3,
            previous_failed_payments=1,
            total_amount_paid=Decimal("15000.00"),
            opted_out=False,
        )
        db.add(customer)
        await db.flush()

    payment_id = f"pay_{uuid.uuid4().hex[:14]}"
    txn = Transaction(
        id=payment_id,
        customer_id=customer.id,
        amount=req.amount,
        currency="INR",
        failure_code=req.failure_code,
        status=PaymentStatus.FAILED,
        revenue_at_risk=req.amount,
        amount_recovered=Decimal("0"),
        risk_score=0.25 if req.failure_code != FailureCode.FRAUD_RISK else 0.95,
        recovery_probability=0.85 if req.failure_code != FailureCode.FRAUD_RISK else 0.0,
        retry_count=0,
        message_count=0,
        failed_at=datetime.now(timezone.utc),
    )
    db.add(txn)
    await db.commit()

    res = await db.execute(
        select(Transaction).options(selectinload(Transaction.customer)).where(Transaction.id == payment_id)
    )
    saved = res.scalar_one()
    return TransactionRead.model_validate(saved)




@router.get("", response_model=TransactionListResponse)
async def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: Optional[PaymentStatus] = None,
    failure_code: Optional[FailureCode] = None,
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size
    q = select(Transaction).options(selectinload(Transaction.customer))
    if status:
        q = q.where(Transaction.status == status)
    if failure_code:
        q = q.where(Transaction.failure_code == failure_code)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar()

    q = q.order_by(Transaction.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(q)
    transactions = result.scalars().all()

    return TransactionListResponse(
        items=[TransactionRead.model_validate(t) for t in transactions],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/{payment_id}", response_model=PaymentDetailResponse)
async def get_payment(payment_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Transaction)
        .options(
            selectinload(Transaction.customer),
            selectinload(Transaction.classifications),
            selectinload(Transaction.recovery_actions),
            selectinload(Transaction.audit_events),
        )
        .where(Transaction.id == payment_id)
    )
    txn = result.scalar_one_or_none()
    if txn is None:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")

    return PaymentDetailResponse(
        transaction=TransactionRead.model_validate(txn),
        customer=CustomerRead.model_validate(txn.customer),
        classifications=[
            ClassificationOutput(
                category=c.category,
                confidence=c.confidence,
                reason=c.reason or "",
                method=c.method,
            )
            for c in txn.classifications
        ],
        recovery_actions=[RecoveryActionRead.model_validate(a) for a in txn.recovery_actions],
        audit_trail=[AuditEventRead.model_validate(e) for e in sorted(txn.audit_events, key=lambda x: x.timestamp)],
    )
