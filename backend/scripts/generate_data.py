"""
Synthetic payment data generator.
Produces 500 realistic failed payment records covering all failure types,
edge cases, and expected recovery outcomes.
"""
from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, init_db
from app.models.db_models import (
    Customer, Transaction, AuditEvent,
    FailureCode, FailureCategory, PaymentStatus,
    CustomerSegment, EventType, ClassificationMethod,
    Classification,
)

fake = Faker("en_IN")
random.seed(42)

# ─── Distribution config ────────────────────────────────────────────────────────

FAILURE_DISTRIBUTION: Dict[FailureCode, Dict] = {
    FailureCode.INSUFFICIENT_FUNDS: {
        "weight": 25,
        "amount_range": (500, 25000),
        "expected_outcome": "RECOVERED",
    },
    FailureCode.BANK_TIMEOUT: {
        "weight": 20,
        "amount_range": (1000, 50000),
        "expected_outcome": "RECOVERED",
    },
    FailureCode.NETWORK_ERROR: {
        "weight": 15,
        "amount_range": (500, 30000),
        "expected_outcome": "RECOVERED",
    },
    FailureCode.EXPIRED_CARD: {
        "weight": 15,
        "amount_range": (1000, 20000),
        "expected_outcome": "NOTIFIED",
    },
    FailureCode.CARD_DECLINED: {
        "weight": 12,
        "amount_range": (500, 15000),
        "expected_outcome": "MIXED",
    },
    FailureCode.FRAUD_RISK: {
        "weight": 5,
        "amount_range": (5000, 200000),
        "expected_outcome": "ESCALATED",
    },
    FailureCode.UNKNOWN: {
        "weight": 8,
        "amount_range": (500, 10000),
        "expected_outcome": "HUMAN_REVIEW",
    },
}

SEGMENT_DISTRIBUTION = {
    CustomerSegment.PREMIUM: 20,
    CustomerSegment.REGULAR: 60,
    CustomerSegment.AT_RISK: 20,
}


def weighted_choice(options: Dict) -> str:
    keys = list(options.keys())
    weights = [v["weight"] for v in options.values()]
    return random.choices(keys, weights=weights, k=1)[0]


def segment_choice() -> CustomerSegment:
    keys = list(SEGMENT_DISTRIBUTION.keys())
    weights = list(SEGMENT_DISTRIBUTION.values())
    return random.choices(keys, weights=weights, k=1)[0]


def generate_customers(n: int = 150) -> List[Customer]:
    """Generate a pool of customers."""
    customers = []
    for _ in range(n):
        segment = segment_choice()
        if segment == CustomerSegment.PREMIUM:
            successful = random.randint(10, 50)
            failed = random.randint(0, 3)
            total_paid = Decimal(str(random.uniform(50000, 500000)))
        elif segment == CustomerSegment.REGULAR:
            successful = random.randint(2, 15)
            failed = random.randint(0, 5)
            total_paid = Decimal(str(random.uniform(5000, 50000)))
        else:  # AT_RISK
            successful = random.randint(0, 5)
            failed = random.randint(3, 15)
            total_paid = Decimal(str(random.uniform(0, 10000)))

        customers.append(Customer(
            id=uuid.uuid4(),
            name=fake.name(),
            email=fake.unique.email(),
            phone=fake.phone_number()[:20],
            segment=segment,
            previous_successful_payments=successful,
            previous_failed_payments=failed,
            total_amount_paid=total_paid.quantize(Decimal("0.01")),
            opted_out=random.random() < 0.02,  # 2% opted out
        ))
    return customers


def generate_transactions(
    customers: List[Customer],
    n: int = 500,
) -> List[Transaction]:
    """Generate n failed payment transactions with varied scenarios."""
    transactions = []
    failure_codes = list(FAILURE_DISTRIBUTION.keys())
    failure_weights = [FAILURE_DISTRIBUTION[fc]["weight"] for fc in failure_codes]

    for i in range(n):
        customer = random.choice(customers)
        failure_code = random.choices(failure_codes, weights=failure_weights, k=1)[0]
        config = FAILURE_DISTRIBUTION[failure_code]

        amount = Decimal(str(
            random.uniform(*config["amount_range"])
        )).quantize(Decimal("0.01"))

        failed_at = datetime.utcnow() - timedelta(
            hours=random.randint(1, 72)
        )

        # Edge cases
        retry_count = 0
        status = PaymentStatus.FAILED

        # Some payments already exhausted retries
        if random.random() < 0.05:
            retry_count = 3
            status = PaymentStatus.EXHAUSTED

        # Some already recovered (for testing ALREADY_PAID stopping)
        if random.random() < 0.03:
            status = PaymentStatus.RECOVERED

        txn = Transaction(
            id=f"PAY_{i+1000:05d}",
            customer_id=customer.id,
            amount=amount,
            currency="INR",
            failure_code=failure_code,
            status=status,
            retry_count=retry_count,
            message_count=0,
            risk_score=0.0,          # computed by agent
            recovery_probability=0.0, # computed by agent
            revenue_at_risk=amount,
            amount_recovered=amount if status == PaymentStatus.RECOVERED else Decimal("0"),
            failed_at=failed_at,
            recovered_at=datetime.utcnow() if status == PaymentStatus.RECOVERED else None,
        )
        transactions.append(txn)

    return transactions


async def seed_database(n_customers: int = 150, n_payments: int = 500) -> None:
    """Seed the database with synthetic data."""
    await init_db()

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        from sqlalchemy import select, func
        result = await session.execute(select(func.count()).select_from(Transaction))
        count = result.scalar()
        if count and count > 0:
            print(f"Database already has {count} transactions. Skipping seed.")
            return

        print(f"Generating {n_customers} customers...")
        customers = generate_customers(n_customers)
        session.add_all(customers)
        await session.flush()

        print(f"Generating {n_payments} transactions...")
        transactions = generate_transactions(customers, n_payments)
        session.add_all(transactions)
        await session.flush()

        # Seed initial audit event for each transaction
        events = [
            AuditEvent(
                transaction_id=txn.id,
                event_type=EventType.PAYMENT_FAILED,
                node="external_gateway",
                reason=f"Payment failed with code: {txn.failure_code.value}",
                result="FAILED",
                metadata={"failure_code": txn.failure_code.value, "amount": str(txn.amount)},
                timestamp=txn.failed_at,
            )
            for txn in transactions
            if txn.status == PaymentStatus.FAILED
        ]
        session.add_all(events)
        await session.commit()

        print(f"✅ Seeded {len(customers)} customers and {len(transactions)} transactions.")
        print(f"   Failure distribution:")
        from collections import Counter
        dist = Counter(t.failure_code for t in transactions)
        for code, cnt in sorted(dist.items()):
            print(f"   {code.value:25s} {cnt:4d} payments")


if __name__ == "__main__":
    asyncio.run(seed_database())
