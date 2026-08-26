"""
INGEST_PAYMENT node — loads transaction + customer data and populates state.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agent.state import GraphState, AuditEventEntry
from app.models.db_models import Transaction, Customer, EventType, PaymentStatus
from app.config import get_settings

settings = get_settings()


async def ingest_payment_node(state: GraphState, db: AsyncSession) -> dict:
    """
    Load payment and customer data from database.
    Returns partial state update.
    """
    node_name = "ingest_payment"
    now = datetime.utcnow()

    result = await db.execute(
        select(Transaction)
        .options(selectinload(Transaction.customer))
        .where(Transaction.id == state.payment_id)
    )
    txn: Transaction | None = result.scalar_one_or_none()

    if txn is None:
        raise ValueError(f"Transaction {state.payment_id} not found in database.")

    customer: Customer = txn.customer

    audit = AuditEventEntry(
        event_type=EventType.PAYMENT_INGESTED,
        node=node_name,
        reason=f"Loaded payment {txn.id} — ₹{txn.amount} — {txn.failure_code.value}",
        result="OK",
        metadata={
            "amount": str(txn.amount),
            "failure_code": txn.failure_code.value,
            "customer_segment": customer.segment.value,
            "retry_count": txn.retry_count,
        },
        timestamp=now,
    )

    return {
        "customer_id": str(customer.id),
        "amount": txn.amount,
        "currency": txn.currency,
        "failure_code": txn.failure_code,
        "payment_status": txn.status,
        "retry_count": txn.retry_count,
        "message_count": txn.message_count,
        "revenue_at_risk": txn.amount,  # full amount is at risk
        "amount_recovered": txn.amount_recovered,
        "previous_successful_payments": customer.previous_successful_payments,
        "previous_failed_payments": customer.previous_failed_payments,
        "customer_segment": customer.segment,
        "customer_opted_out": customer.opted_out,
        "failed_at": txn.failed_at,
        "max_retries": settings.max_retries,
        "max_messages": settings.max_customer_messages,
        "recovery_window_days": settings.recovery_window_days,
        "timestamps": {**state.timestamps, node_name: now},
        "audit_events": state.audit_events + [audit],
    }
