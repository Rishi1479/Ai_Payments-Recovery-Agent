"""
ROOT_CAUSE_CLASSIFICATION node.
Uses deterministic mapping for known codes.
Invokes LLM only for UNKNOWN failure codes.
"""
from datetime import datetime

from app.agent.state import GraphState, AuditEventEntry
from app.models.db_models import FailureCode, FailureCategory, EventType, ClassificationMethod
from app.services.classification import classify_deterministic, classify_with_llm


async def root_cause_classification_node(state: GraphState, db=None) -> dict:
    node_name = "root_cause_classification"
    now = datetime.utcnow()

    if state.failure_code != FailureCode.UNKNOWN:
        # Fast deterministic path — no LLM call
        result = classify_deterministic(state.failure_code)
        assert result is not None  # all non-UNKNOWN codes are mapped
    else:
        # LLM path — only for genuinely unknown failure codes
        result = await classify_with_llm(
            payment_id=state.payment_id,
            failure_code=state.failure_code,
            amount=float(state.amount),
        )

    audit = AuditEventEntry(
        event_type=EventType.ROOT_CAUSE_CLASSIFIED,
        node=node_name,
        reason=result.reason,
        result=f"{result.category.value} (confidence={result.confidence:.2f}, method={result.method.value})",
        metadata={
            "failure_code": state.failure_code.value,
            "category": result.category.value,
            "confidence": result.confidence,
            "method": result.method.value,
        },
        timestamp=now,
    )

    return {
        "failure_category": result.category,
        "classification_confidence": result.confidence,
        "classification_method": result.method,
        "classification_reason": result.reason,
        "timestamps": {**state.timestamps, node_name: now},
        "audit_events": state.audit_events + [audit],
    }
