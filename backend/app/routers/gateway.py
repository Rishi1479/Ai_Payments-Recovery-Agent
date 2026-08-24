"""Mock gateway API router."""
from fastapi import APIRouter
from app.gateway.mock_gateway import get_gateway
from app.models.schemas import MockRetryRequest, MockRetryResponse

router = APIRouter(prefix="/api/mock", tags=["mock-gateway"])


@router.post("/payments/{payment_id}/retry", response_model=MockRetryResponse)
async def mock_retry(payment_id: str, req: MockRetryRequest):
    gateway = get_gateway()
    outcome = gateway.retry_payment(
        payment_id=payment_id,
        failure_code=req.failure_code,
    )
    return MockRetryResponse(
        payment_id=payment_id,
        outcome=outcome,
        message=f"Mock gateway outcome: {outcome.value}",
    )


@router.get("/config")
async def get_gateway_config():
    return get_gateway().get_probabilities()


@router.put("/config/{failure_code}")
async def update_gateway_config(failure_code: str, probs: dict[str, float]):
    from app.models.db_models import FailureCode
    gateway = get_gateway()
    gateway.update_probabilities(FailureCode(failure_code), probs)
    return {"message": f"Updated probabilities for {failure_code}", "probs": probs}
