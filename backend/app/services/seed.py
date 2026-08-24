"""
Seed data generator for testing and demo.
Generates realistic customer records and failed transactions.
"""
import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.db_models import (
    Customer, Transaction, CustomerSegment, FailureCode, PaymentStatus
)

CUSTOMER_NAMES = [
    ("Aarav Sharma", "aarav.sharma@example.com", "+919876543210", CustomerSegment.PREMIUM),
    ("Diya Patel", "diya.patel@example.com", "+919876543211", CustomerSegment.REGULAR),
    ("Rohan Iyer", "rohan.iyer@example.com", "+919876543212", CustomerSegment.REGULAR),
    ("Ananya Reddy", "ananya.reddy@example.com", "+919876543213", CustomerSegment.PREMIUM),
    ("Vikram Singh", "vikram.singh@example.com", "+919876543214", CustomerSegment.AT_RISK),
    ("Priya Nair", "priya.nair@example.com", "+919876543215", CustomerSegment.REGULAR),
    ("Kabir Mehta", "kabir.mehta@example.com", "+919876543216", CustomerSegment.PREMIUM),
    ("Sneha Joshi", "sneha.joshi@example.com", "+919876543217", CustomerSegment.REGULAR),
    ("Aditya Gupta", "aditya.gupta@example.com", "+919876543218", CustomerSegment.AT_RISK),
    ("Neha Verma", "neha.verma@example.com", "+919876543219", CustomerSegment.REGULAR),
    ("Rahul Deshmukh", "rahul.deshmukh@example.com", "+919876543220", CustomerSegment.PREMIUM),
    ("Pooja Choudhary", "pooja.choudhary@example.com", "+919876543221", CustomerSegment.REGULAR),
    ("Karan Malhotra", "karan.malhotra@example.com", "+919876543222", CustomerSegment.AT_RISK),
    ("Meera Nambiar", "meera.nambiar@example.com", "+919876543223", CustomerSegment.PREMIUM),
    ("Siddharth Rao", "siddharth.rao@example.com", "+919876543224", CustomerSegment.REGULAR),
]

FAILURE_DISTRIBUTION = [
    (FailureCode.INSUFFICIENT_FUNDS, 0.35),
    (FailureCode.BANK_TIMEOUT, 0.25),
    (FailureCode.NETWORK_ERROR, 0.15),
    (FailureCode.CARD_DECLINED, 0.10),
    (FailureCode.EXPIRED_CARD, 0.08),
    (FailureCode.FRAUD_RISK, 0.05),
    (FailureCode.UNKNOWN, 0.02),
]


async def seed_database(db: AsyncSession, count: int = 50) -> int:
    """Populate database with sample customers and failed payments."""
    customers = []
    # Check existing customers
    res = await db.execute(select(Customer))
    existing_customers = res.scalars().all()

    if not existing_customers:
        for name, email, phone, seg in CUSTOMER_NAMES:
            c = Customer(
                id=uuid.uuid4(),
                name=name,
                email=email,
                phone=phone,
                segment=seg,
                previous_successful_payments=random.randint(1, 20),
                previous_failed_payments=random.randint(0, 3),
                total_amount_paid=Decimal(str(random.randint(1000, 50000))),
                opted_out=(name == "Vikram Singh"), # One sample customer opted out for policy demonstration
            )
            db.add(c)
            customers.append(c)
        await db.flush()
    else:
        customers = list(existing_customers)

    # Generate transactions
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    codes = [item[0] for item in FAILURE_DISTRIBUTION]
    weights = [item[1] for item in FAILURE_DISTRIBUTION]

    added = 0
    for i in range(count):
        pay_id = f"PAY_{random.randint(100000, 999999)}"
        # Check if exists
        exists = await db.get(Transaction, pay_id)
        if exists:
            continue

        cust = random.choice(customers)
        code = random.choices(codes, weights=weights, k=1)[0]
        amount = Decimal(str(random.choice([499, 999, 1499, 2999, 4999, 9999, 15000, 24999])))
        hours_ago = random.randint(1, 72)
        failed_at = now - timedelta(hours=hours_ago)

        txn = Transaction(
            id=pay_id,
            customer_id=cust.id,
            amount=amount,
            currency="INR",
            failure_code=code,
            status=PaymentStatus.FAILED,
            retry_count=0,
            message_count=0,
            revenue_at_risk=amount,
            amount_recovered=Decimal("0"),
            failed_at=failed_at,
            created_at=failed_at,
        )
        db.add(txn)
        added += 1

    await db.commit()
    return added
