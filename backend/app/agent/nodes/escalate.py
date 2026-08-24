"""
ESCALATE node — marks payment for human review.
"""
from datetime import datetime

from app.agent.state import GraphState, AuditEventEntry
from app.models.db_models import ActionOutcome, EventType, PaymentStatus


async def escalate_node(state: GraphState, db=None) -> dict:
    node_name = "escalate"
    now = datetime.utcnow()

    escalation_reason = state.policy_reason or state.action_reason or "Agent escalation — no automated path available."

    audit = AuditEventEntry(
        event_type=EventType.PAYMENT_ESCALATED,
        node=node_name,
        reason=escalation_reason,
        result="ESCALATED",
        metadata={
            "retry_count": state.retry_count,
            "message_count": state.message_count,
            "failure_code": state.failure_code.value,
            "escalation_reason": escalation_reason,
        },
        timestamp=now,
    )

    return {
        "payment_status": PaymentStatus.ESCALATED,
        "action_result": ActionOutcome.FAILED,
        "escalation_reason": escalation_reason,
        "timestamps": {**state.timestamps, node_name: now},
        "audit_events": state.audit_events + [audit],
    }
