"""
SQLAlchemy ORM Models — the single source of truth for DB schema.
Compatible across both SQLite and PostgreSQL.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Column, String, Integer, Float, Numeric, Boolean,
    DateTime, Text, ForeignKey, Enum as SAEnum, JSON,
    Uuid,
)
from sqlalchemy.orm import relationship

from app.database import Base

import enum


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ─── Enums ────────────────────────────────────────────────────────────────────

class FailureCode(str, enum.Enum):
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    BANK_TIMEOUT = "BANK_TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    EXPIRED_CARD = "EXPIRED_CARD"
    CARD_DECLINED = "CARD_DECLINED"
    FRAUD_RISK = "FRAUD_RISK"
    UNKNOWN = "UNKNOWN"


class FailureCategory(str, enum.Enum):
    TEMPORARY_FUNDS = "TEMPORARY_FUNDS"
    TEMPORARY_TECHNICAL = "TEMPORARY_TECHNICAL"
    PAYMENT_METHOD_ISSUE = "PAYMENT_METHOD_ISSUE"
    CARD_DECLINE = "CARD_DECLINE"
    HIGH_RISK = "HIGH_RISK"
    UNKNOWN = "UNKNOWN"


class PaymentStatus(str, enum.Enum):
    FAILED = "FAILED"
    PENDING_RECOVERY = "PENDING_RECOVERY"
    RECOVERED = "RECOVERED"
    ESCALATED = "ESCALATED"
    EXHAUSTED = "EXHAUSTED"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class RecoveryAction(str, enum.Enum):
    RETRY = "RETRY"
    NOTIFY = "NOTIFY"
    ESCALATE = "ESCALATE"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    STOP = "STOP"


class PolicyResult(str, enum.Enum):
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"


class ActionOutcome(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    ALREADY_PAID = "ALREADY_PAID"
    PENDING = "PENDING"


class ClassificationMethod(str, enum.Enum):
    DETERMINISTIC = "DETERMINISTIC"
    LLM = "LLM"


class CustomerSegment(str, enum.Enum):
    PREMIUM = "PREMIUM"
    REGULAR = "REGULAR"
    AT_RISK = "AT_RISK"


class EventType(str, enum.Enum):
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_INGESTED = "PAYMENT_INGESTED"
    RISK_ANALYZED = "RISK_ANALYZED"
    ROOT_CAUSE_CLASSIFIED = "ROOT_CAUSE_CLASSIFIED"
    RECOVERY_DECISION_MADE = "RECOVERY_DECISION_MADE"
    POLICY_APPROVED = "POLICY_APPROVED"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    RETRY_SCHEDULED = "RETRY_SCHEDULED"
    RETRY_ATTEMPTED = "RETRY_ATTEMPTED"
    RETRY_SUCCEEDED = "RETRY_SUCCEEDED"
    RETRY_FAILED = "RETRY_FAILED"
    CUSTOMER_NOTIFIED = "CUSTOMER_NOTIFIED"
    PAYMENT_RECOVERED = "PAYMENT_RECOVERED"
    PAYMENT_ESCALATED = "PAYMENT_ESCALATED"
    PAYMENT_EXHAUSTED = "PAYMENT_EXHAUSTED"
    WORKFLOW_STOPPED = "WORKFLOW_STOPPED"
    HUMAN_REVIEW_REQUESTED = "HUMAN_REVIEW_REQUESTED"


class BatchStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ─── ORM Models ────────────────────────────────────────────────────────────────

class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = {"extend_existing": True}

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(20))
    segment = Column(SAEnum(CustomerSegment, native_enum=False), default=CustomerSegment.REGULAR)
    previous_successful_payments = Column(Integer, default=0)
    previous_failed_payments = Column(Integer, default=0)
    total_amount_paid = Column(Numeric(12, 2), default=Decimal("0"))
    opted_out = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    transactions = relationship("Transaction", back_populates="customer")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = {"extend_existing": True}

    id = Column(String(50), primary_key=True)   # PAY_XXXXX
    customer_id = Column(Uuid(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="INR")
    failure_code = Column(SAEnum(FailureCode, native_enum=False), nullable=False)
    failure_category = Column(SAEnum(FailureCategory, native_enum=False))
    status = Column(SAEnum(PaymentStatus, native_enum=False), default=PaymentStatus.FAILED)
    retry_count = Column(Integer, default=0)
    message_count = Column(Integer, default=0)
    risk_score = Column(Float, default=0.0)
    recovery_probability = Column(Float, default=0.0)
    revenue_at_risk = Column(Numeric(12, 2), default=Decimal("0"))
    amount_recovered = Column(Numeric(12, 2), default=Decimal("0"))
    escalation_reason = Column(Text)
    failed_at = Column(DateTime, nullable=False)
    recovered_at = Column(DateTime)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    customer = relationship("Customer", back_populates="transactions")
    classifications = relationship("Classification", back_populates="transaction")
    recovery_actions = relationship("RecoveryActionRecord", back_populates="transaction")
    audit_events = relationship("AuditEvent", back_populates="transaction")


class Classification(Base):
    __tablename__ = "classifications"
    __table_args__ = {"extend_existing": True}

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(String(50), ForeignKey("transactions.id"), nullable=False)
    category = Column(SAEnum(FailureCategory, native_enum=False), nullable=False)
    confidence = Column(Float, nullable=False)
    reason = Column(Text)
    method = Column(SAEnum(ClassificationMethod, native_enum=False), default=ClassificationMethod.DETERMINISTIC)
    created_at = Column(DateTime, default=utcnow)

    transaction = relationship("Transaction", back_populates="classifications")


class RecoveryActionRecord(Base):
    __tablename__ = "recovery_actions"
    __table_args__ = {"extend_existing": True}

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(String(50), ForeignKey("transactions.id"), nullable=False)
    action_type = Column(SAEnum(RecoveryAction, native_enum=False), nullable=False)
    recommended_by = Column(String(50), default="agent")
    policy_result = Column(SAEnum(PolicyResult, native_enum=False))
    policy_reason = Column(Text)
    outcome = Column(SAEnum(ActionOutcome, native_enum=False), default=ActionOutcome.PENDING)
    outcome_detail = Column(Text)
    executed_at = Column(DateTime, default=utcnow)
    completed_at = Column(DateTime)

    transaction = relationship("Transaction", back_populates="recovery_actions")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = {"extend_existing": True}

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(String(50), ForeignKey("transactions.id"), nullable=False)
    event_type = Column(SAEnum(EventType, native_enum=False), nullable=False)
    node = Column(String(100))
    reason = Column(Text)
    result = Column(Text)
    event_metadata = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=utcnow)

    transaction = relationship("Transaction", back_populates="audit_events")


class BatchRun(Base):
    __tablename__ = "batch_runs"
    __table_args__ = {"extend_existing": True}

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    started_at = Column(DateTime, default=utcnow)
    completed_at = Column(DateTime)
    total_payments = Column(Integer, default=0)
    recovered = Column(Integer, default=0)
    escalated = Column(Integer, default=0)
    exhausted = Column(Integer, default=0)
    human_review = Column(Integer, default=0)
    pending = Column(Integer, default=0)
    revenue_at_risk = Column(Numeric(14, 2), default=Decimal("0"))
    revenue_recovered = Column(Numeric(14, 2), default=Decimal("0"))
    status = Column(SAEnum(BatchStatus, native_enum=False), default=BatchStatus.RUNNING)
    error_message = Column(Text)
