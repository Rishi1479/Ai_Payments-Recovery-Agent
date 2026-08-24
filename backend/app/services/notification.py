"""
Notification service — controlled templates with optional LLM personalization.
LLM cannot generate arbitrary financial instructions.
"""
from __future__ import annotations

from app.models.db_models import FailureCode
from app.config import get_settings

settings = get_settings()

# ─── Controlled notification templates ────────────────────────────────────────
# LLM can personalize tone but cannot alter the financial facts/instructions.

TEMPLATES: dict[FailureCode, str] = {
    FailureCode.EXPIRED_CARD: (
        "Dear {customer_name}, your payment of {currency}{amount} could not be completed "
        "because your saved payment method has expired. Please update your payment details "
        "to complete your transaction."
    ),
    FailureCode.CARD_DECLINED: (
        "Dear {customer_name}, your payment of {currency}{amount} was declined by your bank. "
        "Please contact your bank or try a different payment method."
    ),
    FailureCode.INSUFFICIENT_FUNDS: (
        "Dear {customer_name}, your payment of {currency}{amount} could not be processed "
        "due to insufficient funds. We will retry automatically, or you can update your "
        "payment details."
    ),
    FailureCode.UNKNOWN: (
        "Dear {customer_name}, your payment of {currency}{amount} could not be completed. "
        "Our team is reviewing this and will contact you shortly."
    ),
}

DEFAULT_TEMPLATE = (
    "Dear {customer_name}, your payment of {currency}{amount} was unsuccessful. "
    "Please contact support for assistance."
)


def format_notification(
    failure_code: FailureCode,
    customer_name: str,
    amount: str,
    currency: str = "₹",
) -> str:
    """Return a safe, templated notification message. No LLM involved."""
    template = TEMPLATES.get(failure_code, DEFAULT_TEMPLATE)
    return template.format(
        customer_name=customer_name,
        amount=amount,
        currency=currency,
    )
