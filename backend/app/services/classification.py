"""
Classification service — deterministic mapping + LLM fallback for UNKNOWN.
The LLM is ONLY invoked when failure_code is UNKNOWN and a description is present.
"""
from __future__ import annotations

import json
from langsmith import traceable
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


@traceable(name="gemini_root_cause_classification", run_type="llm")
def _call_gemini_classify(api_key: str, model: str, system_prompt: str, user_msg: str, temperature: float) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            response_mime_type="application/json",
        ),
    )
    return response.text


async def classify_with_llm(
    payment_id: str,
    failure_code: FailureCode,
    amount: float,
    description: str = "",
) -> ClassificationOutput:
    """
    LLM-based classification for ambiguous/UNKNOWN cases.
    Returns structured output. Never invents financial values.
    Uses Google GenAI SDK and is fully traced in LangSmith.
    """
    import asyncio

    system_prompt = """You are a payment failure classifier for a financial revenue recovery system.
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
        raw = await asyncio.to_thread(
            _call_gemini_classify,
            settings.gemini_api_key,
            settings.llm_model,
            system_prompt,
            user_msg,
            settings.llm_temperature,
        )
        
        # Clean response if markdown fences exist
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        data = json.loads(cleaned.strip())
        
        category_str = data.get("category", "UNKNOWN").upper()
        # Fallback category if LLM returned unrecognized string
        try:
            category = FailureCategory(category_str)
        except ValueError:
            category = FailureCategory.UNKNOWN

        confidence = float(data.get("confidence", 0.5))
        reason = data.get("reason", "Classified via Gemini model.")

        result = ClassificationOutput(
            category=category,
            confidence=confidence,
            reason=reason,
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
