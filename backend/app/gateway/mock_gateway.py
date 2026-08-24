"""
Mock Payment Gateway — simulates payment retry outcomes.
All probabilities are configurable and deterministic when seeded.
"""
from __future__ import annotations

import random
from decimal import Decimal
from typing import Dict

from app.models.db_models import FailureCode, ActionOutcome
from app.config import get_settings

settings = get_settings()

# ─── Retry outcome probabilities by failure code ────────────────────────────────
# Format: {failure_code: {outcome: probability}}

DEFAULT_OUTCOME_PROBS: Dict[FailureCode, Dict[ActionOutcome, float]] = {
    FailureCode.BANK_TIMEOUT: {
        ActionOutcome.SUCCESS: 0.78,
        ActionOutcome.FAILED: 0.22,
        ActionOutcome.ALREADY_PAID: 0.00,
    },
    FailureCode.NETWORK_ERROR: {
        ActionOutcome.SUCCESS: 0.82,
        ActionOutcome.FAILED: 0.18,
        ActionOutcome.ALREADY_PAID: 0.00,
    },
    FailureCode.INSUFFICIENT_FUNDS: {
        ActionOutcome.SUCCESS: 0.45,
        ActionOutcome.FAILED: 0.52,
        ActionOutcome.ALREADY_PAID: 0.03,
    },
    FailureCode.CARD_DECLINED: {
        ActionOutcome.SUCCESS: 0.30,
        ActionOutcome.FAILED: 0.65,
        ActionOutcome.ALREADY_PAID: 0.05,
    },
    FailureCode.EXPIRED_CARD: {
        # Should NOT be retried before card update — very low success
        ActionOutcome.SUCCESS: 0.05,
        ActionOutcome.FAILED: 0.95,
        ActionOutcome.ALREADY_PAID: 0.00,
    },
    FailureCode.FRAUD_RISK: {
        # NEVER retried — policy prevents this, but if somehow called, always fails
        ActionOutcome.SUCCESS: 0.00,
        ActionOutcome.FAILED: 1.00,
        ActionOutcome.ALREADY_PAID: 0.00,
    },
    FailureCode.UNKNOWN: {
        ActionOutcome.SUCCESS: 0.25,
        ActionOutcome.FAILED: 0.70,
        ActionOutcome.ALREADY_PAID: 0.05,
    },
}


class MockPaymentGateway:
    """
    Deterministic mock gateway for testing and demo.
    Uses a seeded RNG so results are reproducible.
    Probabilities can be overridden at runtime for experiments.
    """

    def __init__(
        self,
        seed: int | None = None,
        outcome_probs: Dict[FailureCode, Dict[ActionOutcome, float]] | None = None,
    ) -> None:
        self._seed = seed if seed is not None else settings.mock_gateway_seed
        self._rng = random.Random(self._seed)
        self._outcome_probs = outcome_probs or {
            k: dict(v) for k, v in DEFAULT_OUTCOME_PROBS.items()
        }
        # Track call count per payment to make results deterministic per payment
        self._call_counts: Dict[str, int] = {}

    def retry_payment(
        self,
        payment_id: str,
        failure_code: FailureCode,
    ) -> ActionOutcome:
        """
        Simulate a payment retry.
        Returns SUCCESS, FAILED, or ALREADY_PAID.
        Result is deterministic per (payment_id, retry_count).
        """
        call_key = f"{payment_id}:{failure_code.value}"
        self._call_counts[call_key] = self._call_counts.get(call_key, 0) + 1
        call_num = self._call_counts[call_key]

        # Seed per payment+call so result is reproducible
        rng = random.Random(hash((self._seed, call_key, call_num)) & 0xFFFFFFFF)

        probs = self._outcome_probs.get(failure_code, {
            ActionOutcome.SUCCESS: 0.25,
            ActionOutcome.FAILED: 0.75,
            ActionOutcome.ALREADY_PAID: 0.00,
        })
        outcomes = list(probs.keys())
        weights = [probs[o] for o in outcomes]
        return rng.choices(outcomes, weights=weights, k=1)[0]

    def update_probabilities(
        self,
        failure_code: FailureCode,
        probs: Dict[str, float],
    ) -> None:
        """Update outcome probabilities for a failure code (for experiments)."""
        self._outcome_probs[failure_code] = {
            ActionOutcome(k): v for k, v in probs.items()
        }

    def get_probabilities(self) -> Dict[str, Dict[str, float]]:
        return {
            fc.value: {ao.value: p for ao, p in probs.items()}
            for fc, probs in self._outcome_probs.items()
        }


# Singleton instance
_gateway: MockPaymentGateway | None = None


def get_gateway() -> MockPaymentGateway:
    global _gateway
    if _gateway is None:
        _gateway = MockPaymentGateway(seed=settings.mock_gateway_seed)
    return _gateway
