"""
Tests for the classification service.
"""
import pytest
from app.services.classification import classify_deterministic
from app.models.db_models import FailureCode, FailureCategory, ClassificationMethod


class TestDeterministicClassification:
    def test_bank_timeout_classified(self):
        result = classify_deterministic(FailureCode.BANK_TIMEOUT)
        assert result is not None
        assert result.category == FailureCategory.TEMPORARY_TECHNICAL
        assert result.confidence >= 0.90
        assert result.method == ClassificationMethod.DETERMINISTIC

    def test_network_error_classified(self):
        result = classify_deterministic(FailureCode.NETWORK_ERROR)
        assert result is not None
        assert result.category == FailureCategory.TEMPORARY_TECHNICAL

    def test_insufficient_funds_classified(self):
        result = classify_deterministic(FailureCode.INSUFFICIENT_FUNDS)
        assert result is not None
        assert result.category == FailureCategory.TEMPORARY_FUNDS

    def test_expired_card_classified(self):
        result = classify_deterministic(FailureCode.EXPIRED_CARD)
        assert result is not None
        assert result.category == FailureCategory.PAYMENT_METHOD_ISSUE

    def test_card_declined_classified(self):
        result = classify_deterministic(FailureCode.CARD_DECLINED)
        assert result is not None
        assert result.category == FailureCategory.CARD_DECLINE

    def test_fraud_risk_classified_as_high_risk(self):
        result = classify_deterministic(FailureCode.FRAUD_RISK)
        assert result is not None
        assert result.category == FailureCategory.HIGH_RISK
        assert result.confidence >= 0.99

    def test_unknown_returns_none(self):
        """UNKNOWN code should NOT be deterministically classified — returns None."""
        result = classify_deterministic(FailureCode.UNKNOWN)
        assert result is None

    def test_all_known_codes_covered(self):
        """All non-UNKNOWN failure codes must have deterministic classification."""
        known_codes = [fc for fc in FailureCode if fc != FailureCode.UNKNOWN]
        for code in known_codes:
            result = classify_deterministic(code)
            assert result is not None, f"{code} has no deterministic classification"
            assert 0.0 <= result.confidence <= 1.0
