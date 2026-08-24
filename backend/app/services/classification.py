"""
Classification service — deterministic mapping + LLM fallback for UNKNOWN.
The LLM is ONLY invoked when failure_code is UNKNOWN and a description is present.
"""
from __future__ import annotations

import json
from app.models.db_models import FailureCode, FailureCategory, ClassificationMethod
from app.models.schemas import ClassificationOutput
from app.config import get_settings

settings = get_settings()

# ─── Deterministic mapping (covers ~85% of traffic) ───────────────────────────

DETERMINISTIC_MAP: dict[FailureCode, tuple[FailureCategory, float, str]] = {
    FailureCode.INSUFFICIENT_FUNDS: (
        FailureCategory.TEMPORARY_FUNDS,
        0.97,
        "Insufficient balance is a known temporary condition; funds often replenish.",
    ),
    FailureCode.BANK_TIMEOUT: (
        FailureCategory.TEMPORARY_TECHNICAL,
        0.95,
        "Bank-side timeout is a transient infrastructure failure; retry succeeds.",
    ),
    FailureCode.NETWORK_ERROR: (
        FailureCategory.TEMPORARY_TECHNICAL,
        0.94,
        "Network error is a transient connectivity failure; retry is safe.",
    ),
    FailureCode.EXPIRED_CARD: (
        FailureCategory.PAYMENT_METHOD_ISSUE,
        0.99,
        "Expired card requires customer to update payment method.",
    ),
    FailureCode.CARD_DECLINED: (
        FailureCategory.CARD_DECLINE,
        0.88,
        "Card declined — could be issuer policy, daily limit, or fraud block.",
    ),
    FailureCode.FRAUD_RISK: (
        FailureCategory.HIGH_RISK,
        0.99,
        "Fraud risk flag — must never be auto-retried; escalate for manual review.",
    ),
}


def classify_deterministic(failure_code: FailureCode) -> ClassificationOutput | None:
    """
    Return a classification for known failure codes. Returns None for UNKNOWN.
    """
    if failure_code in DETERMINISTIC_MAP:
        category, confidence, reason = DETERMINISTIC_MAP[failure_code]
        return ClassificationOutput(
            category=category,
            confidence=confidence,
            reason=reason,
            method=ClassificationMethod.DETERMINISTIC,
        )
    return None


async def classify_with_llm(
    payment_id: str,
    failure_code: FailureCode,
    amount: float,
    description: str = "",
) -> ClassificationOutput:
    """
    LLM-based classification for ambiguous/UNKNOWN cases.
    Returns structured output. Never invents financial values.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage, SystemMessage
    from pydantic import ValidationError

    llm = ChatGoogleGenerativeAI(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        google_api_key=settings.gemini_api_key,
    )

    system_prompt = """You are a payment failure classifier for a financial system.
Your ONLY job is to classify why a payment failed and return structured JSON.

You MUST return exactly this JSON structure:
{
  "category": "<one of: TEMPORARY_FUNDS | TEMPORARY_TECHNICAL | PAYMENT_METHOD_ISSUE | CARD_DECLINE | HIGH_RISK | UNKNOWN>",
  "confidence": <float between 0.0 and 1.0>,
  "reason": "<concise explanation, max 100 words>"
}

Categories:
- TEMPORARY_FUNDS: Low balance, temporary cash-flow issue
- TEMPORARY_TECHNICAL: Infrastructure/timeout/connectivity issue
- PAYMENT_METHOD_ISSUE: Expired/invalid card, needs update
- CARD_DECLINE: Issuer declined — various reasons
- HIGH_RISK: Fraud flag, suspicious activity
- UNKNOWN: Cannot determine with confidence

Rules:
- Never invent financial values or amounts
- If confidence < 0.70, use category UNKNOWN
- Return ONLY valid JSON, no extra text"""

    user_msg = f"""Payment ID: {payment_id}
Failure code: {failure_code.value}
Amount: ₹{amount}
Additional context: {description or 'None'}

Classify this payment failure."""

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_msg),
        ])
        raw = response.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        result = ClassificationOutput(
            category=FailureCategory(data["category"]),
            confidence=float(data["confidence"]),
            reason=data["reason"],
            method=ClassificationMethod.LLM,
        )
        # If LLM is uncertain, force UNKNOWN
        if result.confidence < settings.min_confidence_threshold:
            result = ClassificationOutput(
                category=FailureCategory.UNKNOWN,
                confidence=result.confidence,
                reason=f"LLM confidence too low ({result.confidence:.2f}): {result.reason}",
                method=ClassificationMethod.LLM,
            )
        return result

    except Exception as exc:
        return ClassificationOutput(
            category=FailureCategory.UNKNOWN,
            confidence=0.0,
            reason=f"Classification error: {str(exc)[:200]}",
            method=ClassificationMethod.LLM,
        )
