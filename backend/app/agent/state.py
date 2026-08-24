"""
Strongly typed LangGraph GraphState.
All fields are defined explicitly — no arbitrary dicts.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field

from app.models.db_models import (
    FailureCode, FailureCategory, PaymentStatus,
    RecoveryAction, PolicyResult, ActionOutcome,
    ClassificationMethod, CustomerSegment, EventType,
)


class AuditEventEntry(BaseModel):
    """In-memory audit event (written to DB at the end of each node)."""
    event_type: EventType
    node: str
    reason: str = ""
    result: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GraphState(BaseModel):
    """
    Complete state object passed through all LangGraph nodes.
    Immutable between nodes — each node returns a partial update dict.
    """

    # ── Payment identity ────────────────────────────────────────────────────
    payment_id: str
    customer_id: str
    amount: Decimal = Decimal("0")
    currency: str = "INR"

    # ── Failure information ─────────────────────────────────────────────────
    failure_code: FailureCode = FailureCode.UNKNOWN
    failure_category: Optional[FailureCategory] = None

    # ── Classification ──────────────────────────────────────────────────────
    classification_confidence: float = 0.0
    classification_method: ClassificationMethod = ClassificationMethod.DETERMINISTIC
    classification_reason: str = ""

    # ── Risk metrics (deterministic) ────────────────────────────────────────
    risk_score: float = 0.0            # 0–1 composite
    recovery_probability: float = 0.0  # 0–1 estimated success rate
    revenue_at_risk: Decimal = Decimal("0")

    # ── Decision ────────────────────────────────────────────────────────────
    recommended_action: Optional[RecoveryAction] = None
    action_reason: str = ""
    action_confidence: float = 0.0

    # ── Policy / bounds ─────────────────────────────────────────────────────
    retry_count: int = 0
    message_count: int = 0
    max_retries: int = 3               # from settings
    max_messages: int = 2
    recovery_window_days: int = 7
    policy_result: Optional[PolicyResult] = None
    policy_reason: str = ""

    # ── Execution ────────────────────────────────────────────────────────────
    action_result: Optional[ActionOutcome] = None
    action_outcome_detail: str = ""

    # ── Final outcome ────────────────────────────────────────────────────────
    payment_status: PaymentStatus = PaymentStatus.FAILED
    amount_recovered: Decimal = Decimal("0")
    escalation_reason: str = ""

    # ── Customer history signals (for risk scoring) ──────────────────────────
    previous_successful_payments: int = 0
    previous_failed_payments: int = 0
    customer_segment: CustomerSegment = CustomerSegment.REGULAR
    customer_opted_out: bool = False
    failed_at: Optional[datetime] = None  # used for recovery window check

    # ── Audit trail (accumulated in-memory, flushed to DB per node) ──────────
    audit_events: List[AuditEventEntry] = Field(default_factory=list)

    # ── Node timing ─────────────────────────────────────────────────────────
    timestamps: Dict[str, datetime] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True
