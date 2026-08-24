"""
POLICY_CHECK node — validates the recommended action against all guardrails.
"""
from datetime import datetime

from app.agent.state import GraphState, AuditEventEntry
from app.models.db_models import EventType, PolicyResult
from app.services.policy_engine import get_policy_engine


async def policy_check_node(state: GraphState, db=None) -> dict:
    node_name = "policy_check"
    now = datetime.utcnow()

    engine = get_policy_engine()

    result = engine.check(
        recommended_action=state.recommended_action,
        payment_status=state.payment_status,
        failure_code=state.failure_code,
        failure_category=state.failure_category,
        retry_count=state.retry_count,
        message_count=state.message_count,
        max_retries=state.max_retries,
        max_messages=state.max_messages,
        customer_opted_out=state.customer_opted_out,
        failed_at=state.failed_at,
        recovery_window_days=state.recovery_window_days,
        classification_confidence=state.classification_confidence,
        amount_recovered=float(state.amount_recovered),
    )

    event_type = (
        EventType.POLICY_APPROVED
        if result.result == PolicyResult.APPROVED
        else EventType.POLICY_BLOCKED
    )

    # If blocked, determine what to do instead
    if result.result == PolicyResult.BLOCKED:
        forced = engine.get_forced_action(
            recommended_action=state.recommended_action,
            policy_result=result.result,
            retry_count=state.retry_count,
            max_retries=state.max_retries,
            message_count=state.message_count,
            max_messages=state.max_messages,
            failure_code=state.failure_code,
        )
        final_action = forced
        action_reason = f"Policy blocked original action. Forced to: {forced.value}. {result.reason}"
    else:
        final_action = state.recommended_action
        action_reason = state.action_reason

    audit = AuditEventEntry(
        event_type=event_type,
        node=node_name,
        reason=result.reason,
        result=result.result.value,
        metadata={
            "original_action": state.recommended_action.value if state.recommended_action else None,
            "final_action": final_action.value,
            "policy_result": result.result.value,
        },
        timestamp=now,
    )

    return {
        "policy_result": result.result,
        "policy_reason": result.reason,
        "recommended_action": final_action,
        "action_reason": action_reason,
        "timestamps": {**state.timestamps, node_name: now},
        "audit_events": state.audit_events + [audit],
    }
