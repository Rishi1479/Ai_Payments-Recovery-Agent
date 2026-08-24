"""
Tests for the Mock Payment Gateway.
"""
import pytest
from app.gateway.mock_gateway import MockPaymentGateway
from app.models.db_models import FailureCode, ActionOutcome


class TestMockGateway:
    def test_deterministic_with_seed(self):
        gw1 = MockPaymentGateway(seed=42)
        gw2 = MockPaymentGateway(seed=42)
        result1 = gw1.retry_payment("PAY_001", FailureCode.BANK_TIMEOUT)
        result2 = gw2.retry_payment("PAY_001", FailureCode.BANK_TIMEOUT)
        assert result1 == result2

    def test_fraud_risk_always_fails(self):
        gw = MockPaymentGateway(seed=42)
        for i in range(20):
            outcome = gw.retry_payment(f"PAY_FRAUD_{i}", FailureCode.FRAUD_RISK)
            assert outcome == ActionOutcome.FAILED, f"FRAUD_RISK should always fail, got {outcome}"

    def test_returns_valid_outcome(self):
        gw = MockPaymentGateway(seed=99)
        valid = {ActionOutcome.SUCCESS, ActionOutcome.FAILED, ActionOutcome.ALREADY_PAID}
        for code in FailureCode:
            outcome = gw.retry_payment("PAY_TEST", code)
            assert outcome in valid

    def test_bank_timeout_high_success_rate(self):
        gw = MockPaymentGateway(seed=1)
        successes = sum(
            1 for i in range(100)
            if gw.retry_payment(f"PAY_{i}", FailureCode.BANK_TIMEOUT) == ActionOutcome.SUCCESS
        )
        assert successes >= 60, f"Expected >=60 successes, got {successes}"

    def test_different_payment_ids_different_results(self):
        gw = MockPaymentGateway(seed=42)
        results = [gw.retry_payment(f"PAY_{i:04d}", FailureCode.INSUFFICIENT_FUNDS) for i in range(50)]
        # Not all should be the same
        unique = len(set(results))
        assert unique > 1, "All payment outcomes are identical — seeding may be broken"

    def test_update_probabilities(self):
        gw = MockPaymentGateway(seed=42)
        gw.update_probabilities(FailureCode.INSUFFICIENT_FUNDS, {
            "SUCCESS": 1.0, "FAILED": 0.0, "ALREADY_PAID": 0.0
        })
        for i in range(20):
            outcome = gw.retry_payment(f"PAY_FUNDS_{i}", FailureCode.INSUFFICIENT_FUNDS)
            assert outcome == ActionOutcome.SUCCESS
