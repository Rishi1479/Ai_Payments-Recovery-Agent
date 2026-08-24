"""
Pydantic schemas for API I/O and LLM structured outputs.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.models.db_models import (
    FailureCode, FailureCategory, PaymentStatus,
    RecoveryAction, PolicyResult, ActionOutcome,
    ClassificationMethod, CustomerSegment, EventType, BatchStatus,
)


# ─── Classification Structured Output ─────────────────────────────────────────

class ClassificationOutput(BaseModel):
    """Structured output returned by the classifier (deterministic or LLM)."""
    category: FailureCategory
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    method: ClassificationMethod = ClassificationMethod.DETERMINISTIC


# ─── Recovery Decision Structured Output ──────────────────────────────────────

class RecoveryDecisionOutput(BaseModel):
    """Structured output from the recovery decision node."""
    action: RecoveryAction
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)


# ─── Policy Check Structured Output ───────────────────────────────────────────

class PolicyCheckOutput(BaseModel):
    result: PolicyResult
    reason: str


# ─── Customer Schemas ──────────────────────────────────────────────────────────

class CustomerBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    email: str
    phone: Optional[str] = None
    segment: CustomerSegment = CustomerSegment.REGULAR
    previous_successful_payments: int = 0
    previous_failed_payments: int = 0
    total_amount_paid: Decimal = Decimal("0")
    opted_out: bool = False


class CustomerCreate(CustomerBase):
    pass


class CustomerRead(CustomerBase):
    id: uuid.UUID
    created_at: datetime


# ─── Transaction Schemas ────────────────────────────────────────────────────────

class TransactionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: uuid.UUID
    amount: Decimal
    currency: str = "INR"
    failure_code: FailureCode
    status: PaymentStatus = PaymentStatus.FAILED


class TransactionRead(TransactionBase):
    failure_category: Optional[FailureCategory] = None
    retry_count: int = 0
    message_count: int = 0
    risk_score: float = 0.0
    recovery_probability: float = 0.0
    revenue_at_risk: Decimal = Decimal("0")
    amount_recovered: Decimal = Decimal("0")
    escalation_reason: Optional[str] = None
    failed_at: datetime
    recovered_at: Optional[datetime] = None
    created_at: datetime
    customer: Optional[CustomerRead] = None


class TransactionListResponse(BaseModel):
    items: List[TransactionRead]
    total: int
    page: int
    page_size: int


# ─── Audit Event Schemas ────────────────────────────────────────────────────────

class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    transaction_id: str
    event_type: EventType
    node: Optional[str] = None
    reason: Optional[str] = None
    result: Optional[str] = None
    event_metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime

    @field_validator("event_metadata", mode="before")
    @classmethod
    def coerce_metadata(cls, v: Any) -> Dict[str, Any]:
        """Safely convert non-dict values (e.g. SQLAlchemy MetaData) to empty dict."""
        if isinstance(v, dict):
            return v
        return {}


# ─── Recovery Action Schemas ────────────────────────────────────────────────────

class RecoveryActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: str
    action_type: RecoveryAction
    recommended_by: str
    policy_result: Optional[PolicyResult] = None
    policy_reason: Optional[str] = None
    outcome: ActionOutcome
    outcome_detail: Optional[str] = None
    executed_at: datetime
    completed_at: Optional[datetime] = None


# ─── Payment Detail (Full) ─────────────────────────────────────────────────────

class PaymentDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction: TransactionRead
    customer: CustomerRead
    classifications: List[ClassificationOutput] = []
    recovery_actions: List[RecoveryActionRead] = []
    audit_trail: List[AuditEventRead] = []


# ─── Analytics Schemas ─────────────────────────────────────────────────────────

class AnalyticsSummary(BaseModel):
    total_revenue_at_risk: Decimal
    total_revenue_recovered: Decimal
    recovery_rate: float              # 0–100
    payments_processed: int
    payments_recovered: int
    payments_escalated: int
    payments_exhausted: int
    payments_pending: int
    payments_human_review: int
    retry_success_rate: float
    avg_processing_time_ms: float
    classification_accuracy: Optional[float] = None


class FailureTypeBreakdown(BaseModel):
    failure_code: str
    total: int
    recovered: int
    escalated: int
    revenue_at_risk: Decimal
    revenue_recovered: Decimal
    recovery_rate: float


class InterventionBreakdown(BaseModel):
    intervention: str
    total_attempted: int
    successful: int
    success_rate: float
    revenue_recovered: Decimal


class FunnelStep(BaseModel):
    stage: str
    count: int
    amount: Decimal


# ─── Batch Schemas ─────────────────────────────────────────────────────────────

class BatchRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_payments: int
    recovered: int
    escalated: int
    exhausted: int
    human_review: int
    pending: int
    revenue_at_risk: Decimal
    revenue_recovered: Decimal
    status: BatchStatus
    error_message: Optional[str] = None

    @property
    def recovery_rate(self) -> float:
        if self.revenue_at_risk == 0:
            return 0.0
        return float(self.revenue_recovered / self.revenue_at_risk * 100)


# ─── Mock Gateway Schemas ──────────────────────────────────────────────────────

class MockRetryRequest(BaseModel):
    payment_id: str
    failure_code: FailureCode


class MockRetryResponse(BaseModel):
    payment_id: str
    outcome: ActionOutcome
    message: str


# ─── Recovery Trigger ──────────────────────────────────────────────────────────

class RecoveryRunRequest(BaseModel):
    payment_id: str


class RecoveryRunResponse(BaseModel):
    payment_id: str
    status: PaymentStatus
    amount_recovered: Decimal
    action_taken: Optional[RecoveryAction] = None
    reason: str
    audit_events: List[AuditEventRead] = []
