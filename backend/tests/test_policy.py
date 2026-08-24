"""
Tests for the Policy Engine — all guardrail rules.
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from app.services.policy_engine import PolicyEngine
from app.models.db_models import (
    FailureCode, FailureCategory, RecoveryAction, PolicyResult, PaymentStatus
)

engine = PolicyEngine()

BASE_KWARGS = dict(
    payment_status=PaymentStatus.FAILED,
    failure_code=FailureCode.BANK_TIMEOUT,
    failure_category=FailureCategory.TEMPORARY_TECHNICAL,
    retry_count=0,
    message_count=0,
    max_retries=3,
    max_messages=2,
    customer_opted_out=False,
    failed_at=datetime.utcnow() - timedelta(hours=1),
    recovery_window_days=7,
    classification_confidence=0.95,
    amount_recovered=0.0,
)


class TestPolicyApproval:
    def test_retry_approved_for_bank_timeout(self):
        result = engine.check(recommended_action=RecoveryAction.RETRY, **BASE_KWARGS)
        assert result.result == PolicyResult.APPROVED

    def test_notify_approved(self):
        result = engine.check(
            recommended_action=RecoveryAction.NOTIFY,
            **{**BASE_KWARGS, "failure_code": FailureCode.EXPIRED_CARD,
               "failure_category": FailureCategory.PAYMENT_METHOD_ISSUE},
        )
        assert result.result == PolicyResult.APPROVED


class TestFraudBlocking:
    def test_fraud_retry_blocked(self):
        result = engine.check(
            recommended_action=RecoveryAction.RETRY,
            **{**BASE_KWARGS, "failure_code": FailureCode.FRAUD_RISK,
               "failure_category": FailureCategory.HIGH_RISK},
        )
        assert result.result == PolicyResult.BLOCKED
        assert "Fraud" in result.reason or "fraud" in result.reason.lower() or "BLOCKED" in result.reason

    def test_fraud_escalate_allowed(self):
        result = engine.check(
            recommended_action=RecoveryAction.ESCALATE,
            **{**BASE_KWARGS, "failure_code": FailureCode.FRAUD_RISK,
               "failure_category": FailureCategory.HIGH_RISK},
        )
        assert result.result == PolicyResult.APPROVED


class TestRetryLimits:
    def test_retry_blocked_at_max(self):
        result = engine.check(
            recommended_action=RecoveryAction.RETRY,
            **{**BASE_KWARGS, "retry_count": 3, "max_retries": 3},
        )
        assert result.result == PolicyResult.BLOCKED

    def test_retry_allowed_below_max(self):
        result = engine.check(
            recommended_action=RecoveryAction.RETRY,
            **{**BASE_KWARGS, "retry_count": 2, "max_retries": 3},
        )
        assert result.result == PolicyResult.APPROVED


class TestMessageLimits:
    def test_notify_blocked_at_max_messages(self):
        result = engine.check(
            recommended_action=RecoveryAction.NOTIFY,
            **{**BASE_KWARGS, "message_count": 2, "max_messages": 2},
        )
        assert result.result == PolicyResult.BLOCKED

    def test_notify_allowed_below_max(self):
        result = engine.check(
            recommended_action=RecoveryAction.NOTIFY,
            **{**BASE_KWARGS, "message_count": 1, "max_messages": 2},
        )
        assert result.result == PolicyResult.APPROVED


class TestDuplicatePaymentPrevention:
    def test_retry_blocked_if_already_recovered(self):
        result = engine.check(
            recommended_action=RecoveryAction.RETRY,
            **{**BASE_KWARGS, "payment_status": PaymentStatus.RECOVERED, "amount_recovered": 1000.0},
        )
        assert result.result == PolicyResult.BLOCKED

    def test_retry_blocked_if_amount_recovered(self):
        result = engine.check(
            recommended_action=RecoveryAction.RETRY,
            **{**BASE_KWARGS, "amount_recovered": 500.0},
        )
        assert result.result == PolicyResult.BLOCKED


class TestCustomerOptOut:
    def test_retry_blocked_for_opted_out_customer(self):
        result = engine.check(
            recommended_action=RecoveryAction.RETRY,
            **{**BASE_KWARGS, "customer_opted_out": True},
        )
        assert result.result == PolicyResult.BLOCKED

    def test_notify_blocked_for_opted_out_customer(self):
        result = engine.check(
            recommended_action=RecoveryAction.NOTIFY,
            **{**BASE_KWARGS, "customer_opted_out": True},
        )
        assert result.result == PolicyResult.BLOCKED

    def test_escalate_allowed_for_opted_out_customer(self):
        result = engine.check(
            recommended_action=RecoveryAction.ESCALATE,
            **{**BASE_KWARGS, "customer_opted_out": True},
        )
        assert result.result == PolicyResult.APPROVED


class TestRecoveryWindow:
    def test_blocked_after_window_expired(self):
        result = engine.check(
            recommended_action=RecoveryAction.RETRY,
            **{**BASE_KWARGS, "failed_at": datetime.utcnow() - timedelta(days=10)},
        )
        assert result.result == PolicyResult.BLOCKED

    def test_allowed_within_window(self):
        result = engine.check(
            recommended_action=RecoveryAction.RETRY,
            **{**BASE_KWARGS, "failed_at": datetime.utcnow() - timedelta(days=3)},
        )
        assert result.result == PolicyResult.APPROVED


class TestLowConfidence:
    def test_retry_blocked_for_low_confidence(self):
        result = engine.check(
            recommended_action=RecoveryAction.RETRY,
            **{**BASE_KWARGS, "classification_confidence": 0.50},
        )
        assert result.result == PolicyResult.BLOCKED

    def test_human_review_allowed_for_low_confidence(self):
        result = engine.check(
            recommended_action=RecoveryAction.HUMAN_REVIEW,
            **{**BASE_KWARGS, "classification_confidence": 0.50},
        )
        assert result.result == PolicyResult.APPROVED
