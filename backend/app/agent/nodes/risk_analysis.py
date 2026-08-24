"""
RISK_ANALYSIS node — deterministic risk scoring. No LLM involved.

Risk Score Formula (0–1):
  Base score from failure type severity
  + customer history penalty
  + time urgency factor
  Capped at 1.0

Recovery Probability Formula:
  Base recovery rate by failure type
  × customer segment multiplier
  × (1 - retry_count / max_retries penalty)
  Capped at [0, 1]
"""
from datetime import datetime, timezone
from decimal import Decimal

from app.agent.state import GraphState, AuditEventEntry
from app.models.db_models import FailureCode, CustomerSegment, EventType

# ─── Failure type base risk scores ────────────────────────────────────────────

FAILURE_RISK_BASE: dict[FailureCode, float] = {
    FailureCode.FRAUD_RISK: 0.95,
    FailureCode.CARD_DECLINED: 0.70,
    FailureCode.EXPIRED_CARD: 0.65,
    FailureCode.INSUFFICIENT_FUNDS: 0.55,
    FailureCode.UNKNOWN: 0.50,
    FailureCode.BANK_TIMEOUT: 0.35,
    FailureCode.NETWORK_ERROR: 0.30,
}

# ─── Base recovery probability by failure type ─────────────────────────────────

FAILURE_RECOVERY_BASE: dict[FailureCode, float] = {
    FailureCode.BANK_TIMEOUT: 0.78,
    FailureCode.NETWORK_ERROR: 0.82,
    FailureCode.INSUFFICIENT_FUNDS: 0.45,
    FailureCode.CARD_DECLINED: 0.30,
    FailureCode.EXPIRED_CARD: 0.40,   # after customer updates card
    FailureCode.UNKNOWN: 0.25,
    FailureCode.FRAUD_RISK: 0.00,     # never auto-recovered
}

# ─── Customer segment multipliers ──────────────────────────────────────────────

SEGMENT_RECOVERY_MULTIPLIER: dict[CustomerSegment, float] = {
    CustomerSegment.PREMIUM: 1.25,
    CustomerSegment.REGULAR: 1.00,
    CustomerSegment.AT_RISK: 0.70,
}

SEGMENT_RISK_PENALTY: dict[CustomerSegment, float] = {
    CustomerSegment.PREMIUM: -0.10,
    CustomerSegment.REGULAR: 0.00,
    CustomerSegment.AT_RISK: +0.15,
}


def compute_risk_score(state: GraphState) -> float:
    """
    Deterministic risk score 0–1.
    Higher = more at risk of NOT being recovered.
    """
    base = FAILURE_RISK_BASE.get(state.failure_code, 0.50)

    # Customer history penalty: many previous failures → higher risk
    history_ratio = (
        state.previous_failed_payments
        / max(state.previous_successful_payments + state.previous_failed_payments, 1)
    )
    history_penalty = history_ratio * 0.15  # max +0.15

    # Segment adjustment
    segment_adj = SEGMENT_RISK_PENALTY.get(state.customer_segment, 0.0)

    # Retry exhaustion: higher retry count → higher risk score
    retry_ratio = state.retry_count / max(state.max_retries, 1)
    retry_penalty = retry_ratio * 0.10

    raw = base + history_penalty + segment_adj + retry_penalty
    return min(max(raw, 0.0), 1.0)


def compute_recovery_probability(state: GraphState) -> float:
    """
    Deterministic recovery probability 0–1.
    Uses failure type base rate, customer signals, retry history.
    """
    base = FAILURE_RECOVERY_BASE.get(state.failure_code, 0.25)

    # Segment multiplier
    multiplier = SEGMENT_RECOVERY_MULTIPLIER.get(state.customer_segment, 1.0)

    # Strong payment history boosts recovery odds
    successful_ratio = (
        state.previous_successful_payments
        / max(state.previous_successful_payments + state.previous_failed_payments, 1)
    )
    history_boost = successful_ratio * 0.10

    # Retry penalty: already tried and failed → lower chance
    retry_penalty = (state.retry_count / max(state.max_retries, 1)) * 0.20

    # Opted-out customers: no notification-based recovery
    if state.customer_opted_out:
        base *= 0.30

    raw = (base + history_boost - retry_penalty) * multiplier
    return min(max(raw, 0.0), 1.0)


async def risk_analysis_node(state: GraphState, db=None) -> dict:
    """
    Compute risk_score and recovery_probability deterministically.
    db parameter is accepted for API signature consistency but not used here.
    """
    node_name = "risk_analysis"
    now = datetime.utcnow()

    risk_score = compute_risk_score(state)
    recovery_probability = compute_recovery_probability(state)

    audit = AuditEventEntry(
        event_type=EventType.RISK_ANALYZED,
        node=node_name,
        reason=(
            f"risk_score={risk_score:.2f}, "
            f"recovery_probability={recovery_probability:.2f}, "
            f"revenue_at_risk=₹{state.amount}"
        ),
        result="OK",
        metadata={
            "risk_score": round(risk_score, 4),
            "recovery_probability": round(recovery_probability, 4),
            "failure_code": state.failure_code.value,
            "customer_segment": state.customer_segment.value,
            "previous_successful": state.previous_successful_payments,
            "previous_failed": state.previous_failed_payments,
        },
        timestamp=now,
    )

    return {
        "risk_score": round(risk_score, 4),
        "recovery_probability": round(recovery_probability, 4),
        "revenue_at_risk": state.amount,
        "timestamps": {**state.timestamps, node_name: now},
        "audit_events": state.audit_events + [audit],
    }
