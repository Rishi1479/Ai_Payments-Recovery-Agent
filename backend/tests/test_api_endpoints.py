"""
Integration tests for FastAPI endpoints.
"""
from decimal import Decimal
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.database import get_db
from app.models.db_models import (
    Customer, Transaction, PaymentStatus, FailureCode, CustomerSegment
)


@pytest.fixture
def override_db(db_session: AsyncSession):
    """Override get_db FastAPI dependency with the test in-memory SQLite session."""
    async def _get_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_db
    yield db_session
    app.dependency_overrides.clear()


@pytest.fixture
async def client(override_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as c:
        yield c


@pytest.mark.asyncio
async def test_health_and_root(client: AsyncClient):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    res_root = await client.get("/")
    assert res_root.status_code == 200
    assert "service" in res_root.json()


@pytest.mark.asyncio
async def test_payments_seed_and_list(client: AsyncClient):
    # Seed 10 payments
    res = await client.post("/api/payments/seed?count=10")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 10

    # List payments
    res_list = await client.get("/api/payments?limit=10")
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["total"] >= 10
    assert len(list_data["items"]) == 10

    # Get first payment details
    first_id = list_data["items"][0]["id"]
    res_detail = await client.get(f"/api/payments/{first_id}")
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert detail_data["transaction"]["id"] == first_id


@pytest.mark.asyncio
async def test_payments_inject(client: AsyncClient):
    payload = {
        "amount": "3499.00",
        "failure_code": "BANK_TIMEOUT",
        "customer_email": "jane.doe@example.com",
    }
    res = await client.post("/api/payments/inject", json=payload)
    assert res.status_code == 200
    tx = res.json()
    assert tx["status"] == "FAILED"
    assert tx["failure_code"] == "BANK_TIMEOUT"
    assert float(tx["amount"]) == 3499.00


@pytest.mark.asyncio
async def test_single_recovery_run(client: AsyncClient, override_db: AsyncSession):
    # Seed and get a payment
    res_seed = await client.post("/api/payments/seed?count=5")
    assert res_seed.status_code == 200

    res_list = await client.get("/api/payments?status=FAILED&limit=1")
    assert res_list.status_code == 200
    items = res_list.json()["items"]
    assert len(items) > 0
    target_id = items[0]["id"]

    # Trigger recovery agent run
    res_run = await client.post(
        "/api/recovery/run",
        json={"payment_id": target_id},
    )
    assert res_run.status_code == 200
    run_data = res_run.json()
    assert run_data["payment_id"] == target_id
    assert run_data["status"] in ["RECOVERED", "FAILED", "ESCALATED", "EXHAUSTED", "HUMAN_REVIEW", "PENDING_RECOVERY"]
    assert len(run_data["audit_events"]) > 0


@pytest.mark.asyncio
async def test_analytics_endpoints(client: AsyncClient):
    # Seed some transactions first
    await client.post("/api/payments/seed?count=15")

    # Analytics summary
    res_summary = await client.get("/api/analytics/summary")
    assert res_summary.status_code == 200
    summary = res_summary.json()
    assert "total_revenue_at_risk" in summary
    assert "total_revenue_recovered" in summary
    assert "recovery_rate" in summary
    assert "payments_processed" in summary

    # Failure types breakdown
    res_ft = await client.get("/api/analytics/failure-types")
    assert res_ft.status_code == 200
    assert isinstance(res_ft.json(), list)

    # Interventions breakdown
    res_inv = await client.get("/api/analytics/by-intervention")
    assert res_inv.status_code == 200
    assert isinstance(res_inv.json(), list)

    # Funnel
    res_funnel = await client.get("/api/analytics/funnel")
    assert res_funnel.status_code == 200
    assert isinstance(res_funnel.json(), list)

    # Daily trend
    res_trend = await client.get("/api/analytics/daily-trend?days=7")
    assert res_trend.status_code == 200
    assert isinstance(res_trend.json(), list)


@pytest.mark.asyncio
async def test_mock_gateway_endpoints(client: AsyncClient):
    # Test retry endpoint
    res_retry = await client.post(
        "/api/mock/payments/pay_testmock123/retry",
        json={"payment_id": "pay_testmock123", "failure_code": "BANK_TIMEOUT"},
    )
    assert res_retry.status_code == 200
    data = res_retry.json()
    assert data["outcome"] in ["SUCCESS", "FAILED"]

    # Test config
    res_cfg = await client.get("/api/mock/config")
    assert res_cfg.status_code == 200
    assert "BANK_TIMEOUT" in res_cfg.json()

    # Test update config
    res_update = await client.put(
        "/api/mock/config/BANK_TIMEOUT",
        json={"SUCCESS": 0.85, "FAILED": 0.15},
    )
    assert res_update.status_code == 200
    assert res_update.json()["probs"]["SUCCESS"] == 0.85
