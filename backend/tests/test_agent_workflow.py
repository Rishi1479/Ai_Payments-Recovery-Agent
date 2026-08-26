"""
Tests for LangGraph agent workflow nodes, edge routing, and decision engine.
"""
import pytest
from datetime import datetime, timezone
from decimal import Decimal
import uuid

from app.agent.state import GraphState, AuditEventEntry
from app.agent.nodes.risk_analysis import (
    risk_analysis_node,
    compute_risk_score,
    compute_recovery_probability,
)
from app.agent.nodes.decision import recovery_decision_node
from app.agent.nodes.policy_check import policy_check_node
from app.agent.nodes.notify import notify_node
from app.agent.nodes.escalate import escalate_node
from app.agent.nodes.retry import retry_node
from app.agent.nodes.outcome import outcome_check_node
from app.agent.graph import route_after_policy, _human_review
from app.models.db_models import (
    FailureCode,
    FailureCategory,
    RecoveryAction,
    PaymentStatus,
    CustomerSegment,
    PolicyResult,
    ActionOutcome,
    EventType,
    Transaction,
    Customer,
)


@pytest.fixture
def base_state():
    return GraphState(
        payment_id="pay_test123",
        customer_id=str(uuid.uuid4()),
        customer_name="Aarav Sharma",
        customer_email="aarav@example.com",
        customer_segment=CustomerSegment.REGULAR,
        customer_opted_out=False,
        previous_successful_payments=5,
        previous_failed_payments=1,
        amount=Decimal("2500.00"),
        currency="INR",
        failure_code=FailureCode.BANK_TIMEOUT,
        failure_category=FailureCategory.TEMPORARY_TECHNICAL,
        classification_confidence=0.90,
        payment_status=PaymentStatus.FAILED,
        retry_count=0,
        message_count=0,
        max_retries=3,
        max_messages=2,
        failed_at=datetime.now(timezone.utc),
    )


class TestRiskAnalysisNode:
    @pytest.mark.asyncio
    async def test_risk_analysis_timeout(self, base_state):
        res = await risk_analysis_node(base_state)
        assert "risk_score" in res
        assert "recovery_probability" in res
        assert 0.0 <= res["risk_score"] <= 1.0
        assert 0.0 <= res["recovery_probability"] <= 1.0
        # Bank timeout should have high recovery probability
        assert res["recovery_probability"] >= 0.5
        assert len(res["audit_events"]) == 1

    def test_risk_score_fraud_vs_timeout(self, base_state):
        base_state.failure_code = FailureCode.FRAUD_RISK
        fraud_risk = compute_risk_score(base_state)
        base_state.failure_code = FailureCode.BANK_TIMEOUT
        timeout_risk = compute_risk_score(base_state)
        assert fraud_risk > timeout_risk

    def test_premium_segment_boost(self, base_state):
        base_state.customer_segment = CustomerSegment.PREMIUM
        prem_prob = compute_recovery_probability(base_state)
        base_state.customer_segment = CustomerSegment.AT_RISK
        at_risk_prob = compute_recovery_probability(base_state)
        assert prem_prob > at_risk_prob


class TestDecisionNode:
    @pytest.mark.asyncio
    async def test_technical_failure_recommends_retry(self, base_state):
        base_state.failure_category = FailureCategory.TEMPORARY_TECHNICAL
        res = await recovery_decision_node(base_state)
        assert res["recommended_action"] == RecoveryAction.RETRY
        assert res["action_confidence"] > 0.8

    @pytest.mark.asyncio
    async def test_expired_card_recommends_notify(self, base_state):
        base_state.failure_category = FailureCategory.PAYMENT_METHOD_ISSUE
        res = await recovery_decision_node(base_state)
        assert res["recommended_action"] == RecoveryAction.NOTIFY

    @pytest.mark.asyncio
    async def test_fraud_recommends_escalate(self, base_state):
        base_state.failure_category = FailureCategory.HIGH_RISK
        res = await recovery_decision_node(base_state)
        assert res["recommended_action"] == RecoveryAction.ESCALATE

    @pytest.mark.asyncio
    async def test_already_recovered_stops(self, base_state):
        base_state.payment_status = PaymentStatus.RECOVERED
        res = await recovery_decision_node(base_state)
        assert res["recommended_action"] == RecoveryAction.STOP


class TestPolicyCheckNode:
    @pytest.mark.asyncio
    async def test_approved_policy(self, base_state):
        base_state.recommended_action = RecoveryAction.RETRY
        res = await policy_check_node(base_state)
        assert res["policy_result"] == PolicyResult.APPROVED
        assert res["recommended_action"] == RecoveryAction.RETRY

    @pytest.mark.asyncio
    async def test_blocked_policy_max_retries_forces_escalate(self, base_state):
        base_state.recommended_action = RecoveryAction.RETRY
        base_state.retry_count = 3
        base_state.max_retries = 3
        res = await policy_check_node(base_state)
        assert res["policy_result"] == PolicyResult.BLOCKED
        assert res["recommended_action"] == RecoveryAction.ESCALATE

    @pytest.mark.asyncio
    async def test_opted_out_customer_blocks_notify(self, base_state):
        base_state.recommended_action = RecoveryAction.NOTIFY
        base_state.customer_opted_out = True
        res = await policy_check_node(base_state)
        assert res["policy_result"] == PolicyResult.BLOCKED
        assert res["recommended_action"] == RecoveryAction.ESCALATE


class TestActionNodes:
    @pytest.mark.asyncio
    async def test_notify_node_increments_count(self, base_state):
        base_state.message_count = 0
        res = await notify_node(base_state)
        assert res["message_count"] == 1
        assert res["action_result"] == ActionOutcome.PENDING
        assert len(res["audit_events"]) == 1

    @pytest.mark.asyncio
    async def test_escalate_node(self, base_state):
        res = await escalate_node(base_state)
        assert res["payment_status"] == PaymentStatus.ESCALATED
        assert res["action_result"] == ActionOutcome.FAILED

    @pytest.mark.asyncio
    async def test_human_review_node(self, base_state):
        res = await _human_review(base_state)
        assert res["payment_status"] == PaymentStatus.HUMAN_REVIEW
        assert res["action_result"] == ActionOutcome.PENDING


class TestRouting:
    def test_route_after_policy_retry(self, base_state):
        base_state.recommended_action = RecoveryAction.RETRY
        assert route_after_policy(base_state) == "retry"

    def test_route_after_policy_notify(self, base_state):
        base_state.recommended_action = RecoveryAction.NOTIFY
        assert route_after_policy(base_state) == "notify"

    def test_route_after_policy_escalate(self, base_state):
        base_state.recommended_action = RecoveryAction.ESCALATE
        assert route_after_policy(base_state) == "escalate"

    def test_route_after_policy_human_review(self, base_state):
        base_state.recommended_action = RecoveryAction.HUMAN_REVIEW
        assert route_after_policy(base_state) == "human_review"

    def test_route_after_policy_recovered_bypasses(self, base_state):
        base_state.payment_status = PaymentStatus.RECOVERED
        assert route_after_policy(base_state) == "outcome_check"
