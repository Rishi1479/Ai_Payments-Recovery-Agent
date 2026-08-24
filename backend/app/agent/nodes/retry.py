"""
RETRY node — calls the Mock Payment Gateway and records outcome.
"""
from datetime import datetime

from app.agent.state import GraphState, AuditEventEntry
from app.models.db_models import ActionOutcome, EventType, PaymentStatus
from app.gateway.mock_gateway import get_gateway


async def retry_node(state: GraphState, db=None) -> dict:
    node_name = "retry"
    now = datetime.utcnow()

    gateway = get_gateway()
    outcome = gateway.retry_payment(
        payment_id=state.payment_id,
        failure_code=state.failure_code,
    )

    new_retry_count = state.retry_count + 1

    if outcome == ActionOutcome.SUCCESS:
        event_type = EventType.RETRY_SUCCEEDED
        outcome_detail = f"Retry #{new_retry_count} succeeded — payment recovered."
    elif outcome == ActionOutcome.ALREADY_PAID:
        event_type = EventType.RETRY_SUCCEEDED
        outcome_detail = "Payment already completed — stopping recovery."
    else:
        event_type = EventType.RETRY_FAILED
        outcome_detail = f"Retry #{new_retry_count} failed."

    audit = AuditEventEntry(
        event_type=event_type,
        node=node_name,
        reason=f"Mock gateway retry attempt #{new_retry_count}",
        result=outcome.value,
        metadata={
            "retry_number": new_retry_count,
            "outcome": outcome.value,
            "failure_code": state.failure_code.value,
        },
        timestamp=now,
    )

    return {
        "retry_count": new_retry_count,
        "action_result": outcome,
        "action_outcome_detail": outcome_detail,
        "timestamps": {**state.timestamps, node_name: now},
        "audit_events": state.audit_events + [audit],
    }
