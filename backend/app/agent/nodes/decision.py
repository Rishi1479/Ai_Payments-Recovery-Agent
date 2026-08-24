"""
RECOVERY_DECISION node — maps failure category + risk signals to action.
Purely deterministic. LLM is NOT involved in this decision.
"""
from datetime import datetime

from app.agent.state import GraphState, AuditEventEntry
from app.models.db_models import (
    FailureCategory, RecoveryAction, EventType, PaymentStatus
)
from app.config import get_settings

settings = get_settings()

# ─── Decision table ─────────────────────────────────────────────────────────────

CATEGORY_ACTION_MAP: dict[FailureCategory, tuple[RecoveryAction, float, str]] = {
    FailureCategory.TEMPORARY_TECHNICAL: (
        RecoveryAction.RETRY,
        0.92,
        "Transient technical failure — retry is the highest-probability recovery path.",
    ),
    FailureCategory.TEMPORARY_FUNDS: (
        RecoveryAction.RETRY,
        0.80,
        "Temporary insufficient funds — retry after cooldown when funds may have replenished.",
    ),
    FailureCategory.CARD_DECLINE: (
        RecoveryAction.RETRY,
        0.65,
        "Card decline may be transient limit/policy issue — one retry warranted.",
    ),
    FailureCategory.PAYMENT_METHOD_ISSUE: (
        RecoveryAction.NOTIFY,
        0.85,
        "Expired/invalid payment method — customer must update before retry can succeed.",
    ),
    FailureCategory.HIGH_RISK: (
        RecoveryAction.ESCALATE,
        0.99,
        "Fraud/high-risk flag — must never be automatically retried. Escalate for review.",
    ),
    FailureCategory.UNKNOWN: (
        RecoveryAction.HUMAN_REVIEW,
        0.50,
        "Unknown failure category — insufficient information for automated decision.",
    ),
}


async def recovery_decision_node(state: GraphState, db=None) -> dict:
    node_name = "recovery_decision"
    now = datetime.utcnow()

    category = state.failure_category

    if category is None:
        # Fallback: classification failed entirely
        action = RecoveryAction.HUMAN_REVIEW
        confidence = 0.30
        reason = "Classification did not produce a category — routing to human review."
    else:
        action, confidence, reason = CATEGORY_ACTION_MAP.get(
            category,
            (RecoveryAction.HUMAN_REVIEW, 0.40, "No decision rule matched — human review required."),
        )

    # Already recovered: no action needed
    if state.payment_status == PaymentStatus.RECOVERED:
        action = RecoveryAction.STOP
        confidence = 1.0
        reason = "Payment is already recovered — stopping workflow."

    audit = AuditEventEntry(
        event_type=EventType.RECOVERY_DECISION_MADE,
        node=node_name,
        reason=reason,
        result=f"{action.value} (confidence={confidence:.2f})",
        metadata={
            "failure_category": category.value if category else "None",
            "recommended_action": action.value,
            "confidence": confidence,
        },
        timestamp=now,
    )

    return {
        "recommended_action": action,
        "action_reason": reason,
        "action_confidence": confidence,
        "timestamps": {**state.timestamps, node_name: now},
        "audit_events": state.audit_events + [audit],
    }
