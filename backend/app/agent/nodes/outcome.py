"""
OUTCOME_CHECK node — determines final state after action.
Writes final state to DB. Emits WORKFLOW_STOPPED event.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.agent.state import GraphState, AuditEventEntry
from app.models.db_models import (
    ActionOutcome, EventType, PaymentStatus,
    Transaction, AuditEvent, Classification, RecoveryActionRecord,
    RecoveryAction,
)


async def outcome_check_node(state: GraphState, db: AsyncSession) -> dict:
    node_name = "outcome_check"
    now = datetime.utcnow()

    # ── Determine final payment status ────────────────────────────────────────
    if state.action_result in (ActionOutcome.SUCCESS, ActionOutcome.ALREADY_PAID):
        final_status = PaymentStatus.RECOVERED
        amount_recovered = state.amount
        event_type = EventType.PAYMENT_RECOVERED
        result_str = f"Payment RECOVERED — ₹{state.amount} recovered."
    elif state.payment_status == PaymentStatus.ESCALATED:
        final_status = PaymentStatus.ESCALATED
        amount_recovered = Decimal("0")
        event_type = EventType.WORKFLOW_STOPPED
        result_str = "Workflow stopped — payment escalated."
    elif state.retry_count >= state.max_retries:
        final_status = PaymentStatus.EXHAUSTED
        amount_recovered = Decimal("0")
        event_type = EventType.PAYMENT_EXHAUSTED
        result_str = f"Payment EXHAUSTED — {state.retry_count} retries attempted."
    elif state.recommended_action == RecoveryAction.HUMAN_REVIEW:
        final_status = PaymentStatus.HUMAN_REVIEW
        amount_recovered = Decimal("0")
        event_type = EventType.HUMAN_REVIEW_REQUESTED
        result_str = "Routed to human review queue."
    else:
        final_status = PaymentStatus.PENDING_RECOVERY
        amount_recovered = Decimal("0")
        event_type = EventType.WORKFLOW_STOPPED
        result_str = "Recovery in progress — awaiting customer action."

    stop_audit = AuditEventEntry(
        event_type=EventType.WORKFLOW_STOPPED,
        node=node_name,
        reason=result_str,
        result=final_status.value,
        metadata={
            "final_status": final_status.value,
            "amount_recovered": str(amount_recovered),
            "retry_count": state.retry_count,
            "message_count": state.message_count,
        },
        timestamp=now,
    )

    all_events = state.audit_events + [stop_audit]

    # ── Persist to database ───────────────────────────────────────────────────
    if db is not None:
        try:
            # Update transaction
            await db.execute(
                update(Transaction)
                .where(Transaction.id == state.payment_id)
                .values(
                    status=final_status,
                    failure_category=state.failure_category,
                    retry_count=state.retry_count,
                    message_count=state.message_count,
                    risk_score=state.risk_score,
                    recovery_probability=state.recovery_probability,
                    amount_recovered=amount_recovered,
                    escalation_reason=state.escalation_reason or None,
                    recovered_at=now if final_status == PaymentStatus.RECOVERED else None,
                    updated_at=now,
                )
            )

            # Persist audit events
            for ae in all_events:
                db.add(AuditEvent(
                    transaction_id=state.payment_id,
                    event_type=ae.event_type,
                    node=ae.node,
                    reason=ae.reason,
                    result=ae.result,
                    event_metadata=ae.metadata,
                    timestamp=ae.timestamp,
                ))

            # Persist classification
            if state.failure_category:
                db.add(Classification(
                    transaction_id=state.payment_id,
                    category=state.failure_category,
                    confidence=state.classification_confidence,
                    reason=state.classification_reason,
                    method=state.classification_method,
                ))

            # Persist recovery action record
            if state.recommended_action and state.recommended_action != RecoveryAction.STOP:
                from app.models.db_models import ActionOutcome as AO
                db.add(RecoveryActionRecord(
                    transaction_id=state.payment_id,
                    action_type=state.recommended_action,
                    recommended_by="agent",
                    policy_result=state.policy_result,
                    policy_reason=state.policy_reason,
                    outcome=state.action_result or AO.PENDING,
                    outcome_detail=state.action_outcome_detail,
                    completed_at=now,
                ))

            await db.commit()
        except Exception as exc:
            await db.rollback()
            # Don't crash the workflow — log the error
            print(f"[outcome_check] DB persist error for {state.payment_id}: {exc}")

    return {
        "payment_status": final_status,
        "amount_recovered": amount_recovered,
        "timestamps": {**state.timestamps, node_name: now},
        "audit_events": all_events,
    }
