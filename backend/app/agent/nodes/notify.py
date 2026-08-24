"""
NOTIFY node — sends templated customer notification.
"""
from datetime import datetime

from app.agent.state import GraphState, AuditEventEntry
from app.models.db_models import ActionOutcome, EventType
from app.services.notification import format_notification


async def notify_node(state: GraphState, db=None) -> dict:
    node_name = "notify"
    now = datetime.utcnow()

    message = format_notification(
        failure_code=state.failure_code,
        customer_name=state.customer_id,  # in real system: load customer name
        amount=str(state.amount),
        currency="₹",
    )

    new_message_count = state.message_count + 1

    audit = AuditEventEntry(
        event_type=EventType.CUSTOMER_NOTIFIED,
        node=node_name,
        reason=f"Notification sent (message #{new_message_count}): {state.failure_code.value}",
        result="SENT",
        metadata={
            "message_number": new_message_count,
            "failure_code": state.failure_code.value,
            "message_preview": message[:100],
        },
        timestamp=now,
    )

    return {
        "message_count": new_message_count,
        "action_result": ActionOutcome.PENDING,  # awaiting customer action
        "action_outcome_detail": f"Notification sent to customer. Awaiting action.",
        "timestamps": {**state.timestamps, node_name: now},
        "audit_events": state.audit_events + [audit],
    }
