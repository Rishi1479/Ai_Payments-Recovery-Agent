"""
LangGraph state machine — the core recovery agent.

START
 ↓
INGEST_PAYMENT
 ↓
RISK_ANALYSIS
 ↓
ROOT_CAUSE_CLASSIFICATION
 ↓
RECOVERY_DECISION
 ↓
POLICY_CHECK
 ↓
 ┌──────────────┬───────────────┬────────────────┐
RETRY         NOTIFY         ESCALATE      HUMAN_REVIEW
 └──────────────┴───────────────┴────────────────┘
                 ↓
            OUTCOME_CHECK
              ↙       ↘
           END        END
"""
from __future__ import annotations

from typing import Literal

from langgraph.graph import StateGraph, END

from app.agent.state import GraphState
from app.models.db_models import RecoveryAction, PaymentStatus


# ── Node wrappers (inject db lazily) ────────────────────────────────────────────

async def _ingest(state: GraphState) -> dict:
    from app.database import AsyncSessionLocal
    from app.agent.nodes.ingest import ingest_payment_node
    async with AsyncSessionLocal() as db:
        return await ingest_payment_node(state, db)


async def _risk_analysis(state: GraphState) -> dict:
    from app.agent.nodes.risk_analysis import risk_analysis_node
    return await risk_analysis_node(state)


async def _root_cause(state: GraphState) -> dict:
    from app.agent.nodes.root_cause import root_cause_classification_node
    return await root_cause_classification_node(state)


async def _decision(state: GraphState) -> dict:
    from app.agent.nodes.decision import recovery_decision_node
    return await recovery_decision_node(state)


async def _policy_check(state: GraphState) -> dict:
    from app.agent.nodes.policy_check import policy_check_node
    return await policy_check_node(state)


async def _retry(state: GraphState) -> dict:
    from app.agent.nodes.retry import retry_node
    return await retry_node(state)


async def _notify(state: GraphState) -> dict:
    from app.agent.nodes.notify import notify_node
    return await notify_node(state)


async def _escalate(state: GraphState) -> dict:
    from app.agent.nodes.escalate import escalate_node
    return await escalate_node(state)


async def _outcome(state: GraphState) -> dict:
    from app.database import AsyncSessionLocal
    from app.agent.nodes.outcome import outcome_check_node
    async with AsyncSessionLocal() as db:
        return await outcome_check_node(state, db)


# ── Conditional routing functions ───────────────────────────────────────────────

def route_after_policy(
    state: GraphState,
) -> Literal["retry", "notify", "escalate", "human_review", "outcome_check"]:
    """Route to the appropriate action node based on validated action."""
    action = state.recommended_action

    # Already recovered or stopped
    if state.payment_status == PaymentStatus.RECOVERED:
        return "outcome_check"
    if state.payment_status in (PaymentStatus.ESCALATED, PaymentStatus.EXHAUSTED):
        return "escalate"

    match action:
        case RecoveryAction.RETRY:
            return "retry"
        case RecoveryAction.NOTIFY:
            return "notify"
        case RecoveryAction.ESCALATE:
            return "escalate"
        case RecoveryAction.HUMAN_REVIEW:
            return "human_review"
        case RecoveryAction.STOP:
            return "outcome_check"
        case _:
            return "escalate"


async def _human_review(state: GraphState) -> dict:
    """Human review node — marks payment and stops."""
    from datetime import datetime
    from app.agent.state import AuditEventEntry
    from app.models.db_models import EventType, PaymentStatus, ActionOutcome
    now = datetime.utcnow()
    audit = AuditEventEntry(
        event_type=EventType.HUMAN_REVIEW_REQUESTED,
        node="human_review",
        reason=state.classification_reason or "Low confidence / unknown failure — routed to human.",
        result="HUMAN_REVIEW",
        metadata={"confidence": state.classification_confidence},
        timestamp=now,
    )
    return {
        "payment_status": PaymentStatus.HUMAN_REVIEW,
        "action_result": ActionOutcome.PENDING,
        "audit_events": state.audit_events + [audit],
        "timestamps": {**state.timestamps, "human_review": now},
    }


# ── Graph builder ───────────────────────────────────────────────────────────────

def build_recovery_graph() -> StateGraph:
    builder = StateGraph(GraphState)

    # Add all nodes
    builder.add_node("ingest_payment", _ingest)
    builder.add_node("risk_analysis", _risk_analysis)
    builder.add_node("root_cause_classification", _root_cause)
    builder.add_node("recovery_decision", _decision)
    builder.add_node("policy_check", _policy_check)
    builder.add_node("retry", _retry)
    builder.add_node("notify", _notify)
    builder.add_node("escalate", _escalate)
    builder.add_node("human_review", _human_review)
    builder.add_node("outcome_check", _outcome)

    # Linear flow up to policy check
    builder.set_entry_point("ingest_payment")
    builder.add_edge("ingest_payment", "risk_analysis")
    builder.add_edge("risk_analysis", "root_cause_classification")
    builder.add_edge("root_cause_classification", "recovery_decision")
    builder.add_edge("recovery_decision", "policy_check")

    # Conditional branching after policy check
    builder.add_conditional_edges(
        "policy_check",
        route_after_policy,
        {
            "retry": "retry",
            "notify": "notify",
            "escalate": "escalate",
            "human_review": "human_review",
            "outcome_check": "outcome_check",
        },
    )

    # All action nodes flow to outcome_check
    builder.add_edge("retry", "outcome_check")
    builder.add_edge("notify", "outcome_check")
    builder.add_edge("escalate", "outcome_check")
    builder.add_edge("human_review", "outcome_check")
    builder.add_edge("outcome_check", END)

    return builder.compile()


# Compiled graph singleton
_graph = None


def get_recovery_graph():
    global _graph
    if _graph is None:
        _graph = build_recovery_graph()
    return _graph
