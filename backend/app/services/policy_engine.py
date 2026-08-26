"""
Policy Engine — deterministic guardrail service.
The LLM CANNOT override this layer.
Every action must pass policy validation before execution.

Architecture:
  LLM recommends action
       ↓
  Policy engine validates
       ↓
  APPROVED → execute
  BLOCKED  → stop / escalate
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.db_models import (
    FailureCode, FailureCategory, RecoveryAction,
    PolicyResult, PaymentStatus,
)
from app.models.schemas import PolicyCheckOutput
from app.config import get_settings

settings = get_settings()


class PolicyEngine:
    """
    Stateless deterministic policy checker.
    All limits come from settings (configurable).
    """

    def check(
        self,
        *,
        recommended_action: RecoveryAction,
        payment_status: PaymentStatus,
        failure_code: FailureCode,
        failure_category: FailureCategory | None,
        retry_count: int,
        message_count: int,
        max_retries: int,
        max_messages: int,
        customer_opted_out: bool,
        failed_at: datetime | None,
        recovery_window_days: int,
        classification_confidence: float,
        amount_recovered: float,
    ) -> PolicyCheckOutput:
        """
        Validate a proposed action against all guardrail rules.
        Returns APPROVED or BLOCKED with reason.
        """

        # ── STOP 1: Payment already recovered ──────────────────────────────
        if payment_status == PaymentStatus.RECOVERED or amount_recovered > 0:
            return PolicyCheckOutput(
                result=PolicyResult.BLOCKED,
                reason="STOP: Payment already recovered. Duplicate action prevented.",
            )

        # ── STOP 2: Customer opted out ──────────────────────────────────────
        if customer_opted_out and recommended_action in (
            RecoveryAction.NOTIFY, RecoveryAction.RETRY
        ):
            return PolicyCheckOutput(
                result=PolicyResult.BLOCKED,
                reason="STOP: Customer has opted out of recovery communications.",
            )

        # ── STOP 3: Fraud risk — never auto-retry ──────────────────────────
        if failure_code == FailureCode.FRAUD_RISK and recommended_action == RecoveryAction.RETRY:
            return PolicyCheckOutput(
                result=PolicyResult.BLOCKED,
                reason="BLOCKED: Fraud-risk payments must never be automatically retried. Escalate required.",
            )

        if failure_category and failure_category.value == "HIGH_RISK" and recommended_action == RecoveryAction.RETRY:
            return PolicyCheckOutput(
                result=PolicyResult.BLOCKED,
                reason="BLOCKED: HIGH_RISK category cannot be auto-retried.",
            )

        # ── STOP 4: Max retries exceeded ────────────────────────────────────
        if recommended_action == RecoveryAction.RETRY and retry_count >= max_retries:
            return PolicyCheckOutput(
                result=PolicyResult.BLOCKED,
                reason=f"BLOCKED: Max retries ({max_retries}) already reached. Escalate.",
            )

        # ── STOP 5: Max customer messages exceeded ───────────────────────────
        if recommended_action == RecoveryAction.NOTIFY and message_count >= max_messages:
            return PolicyCheckOutput(
                result=PolicyResult.BLOCKED,
                reason=f"BLOCKED: Max customer messages ({max_messages}) already sent. Escalate.",
            )

        # ── STOP 6: Recovery window expired ─────────────────────────────────
        if failed_at is not None:
            now_dt = datetime.now(timezone.utc) if failed_at.tzinfo else datetime.utcnow()
            window_limit = failed_at + timedelta(days=recovery_window_days)
            if now_dt > window_limit:
                return PolicyCheckOutput(
                    result=PolicyResult.BLOCKED,
                    reason=f"BLOCKED: Recovery window of {recovery_window_days} days expired.",
                )

        # ── STOP 7: Low-confidence classification → human review only ────────
        if (
            classification_confidence < settings.min_confidence_threshold
            and recommended_action not in (
                RecoveryAction.HUMAN_REVIEW, RecoveryAction.ESCALATE
            )
        ):
            return PolicyCheckOutput(
                result=PolicyResult.BLOCKED,
                reason=(
                    f"BLOCKED: Classification confidence {classification_confidence:.2f} "
                    f"below threshold {settings.min_confidence_threshold}. "
                    "Only HUMAN_REVIEW or ESCALATE allowed."
                ),
            )

        # ── STOP 8: Already exhausted ────────────────────────────────────────
        if payment_status == PaymentStatus.EXHAUSTED:
            return PolicyCheckOutput(
                result=PolicyResult.BLOCKED,
                reason="BLOCKED: Payment already exhausted all recovery attempts.",
            )

        # ── PASS ─────────────────────────────────────────────────────────────
        return PolicyCheckOutput(
            result=PolicyResult.APPROVED,
            reason=f"APPROVED: Action {recommended_action.value} passes all guardrail checks.",
        )

    def get_forced_action(
        self,
        *,
        recommended_action: RecoveryAction,
        policy_result: PolicyResult,
        retry_count: int,
        max_retries: int,
        message_count: int,
        max_messages: int,
        failure_code: FailureCode,
    ) -> RecoveryAction:
        """
        When policy blocks an action, determine what forced action to take.
        """
        if policy_result == PolicyResult.APPROVED:
            return recommended_action

        # Fraud → always escalate
        if failure_code == FailureCode.FRAUD_RISK:
            return RecoveryAction.ESCALATE

        # Retries exhausted → escalate
        if retry_count >= max_retries:
            return RecoveryAction.ESCALATE

        # Messages exhausted → escalate
        if message_count >= max_messages:
            return RecoveryAction.ESCALATE

        # Default blocked → escalate
        return RecoveryAction.ESCALATE


# Singleton
_policy_engine: PolicyEngine | None = None


def get_policy_engine() -> PolicyEngine:
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    return _policy_engine
