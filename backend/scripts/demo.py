#!/usr/bin/env python3
"""
One-command demo script.
1. Seeds 500 synthetic payments
2. Runs the batch recovery agent
3. Prints full results report
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scripts.generate_data import seed_database
from app.workers.batch_processor import run_batch
from app.database import AsyncSessionLocal
from app.services.analytics import get_summary, get_failure_type_breakdown


async def main():
    print("=" * 60)
    print("  AI Revenue Recovery Agent — Demo")
    print("=" * 60)

    print("\n📦 Step 1: Seeding 500 synthetic payments...")
    await seed_database(n_customers=150, n_payments=500)

    print("\n🤖 Step 2: Running batch recovery agent...")
    results = await run_batch(concurrency=20, llm_concurrency=5)

    print("\n📊 Step 3: Results")
    print("-" * 60)
    print(f"  Total payments processed : {results['total']}")
    print(f"  Successfully recovered   : {results['recovered']}")
    print(f"  Escalated                : {results['escalated']}")
    print(f"  Exhausted retries        : {results['exhausted']}")
    print(f"  Human review             : {results['human_review']}")
    print(f"  Processing errors        : {results['errors']}")
    print(f"  Revenue recovered        : ₹{float(results['revenue_recovered']):,.2f}")
    print(f"  Total elapsed            : {results['elapsed_seconds']:.1f}s")
    print(f"  Throughput               : {results['throughput_per_sec']} payments/sec")
    print(f"  Avg latency              : {results['avg_latency_ms']:.0f}ms/payment")

    print("\n📈 Step 4: Analytics Summary")
    print("-" * 60)
    async with AsyncSessionLocal() as db:
        summary = await get_summary(db)
        print(f"  Revenue at risk          : ₹{float(summary.total_revenue_at_risk):,.2f}")
        print(f"  Revenue recovered        : ₹{float(summary.total_revenue_recovered):,.2f}")
        print(f"  Recovery rate            : {summary.recovery_rate:.1f}%")
        print(f"  Retry success rate       : {summary.retry_success_rate:.1f}%")

        print("\n📋 Breakdown by failure type:")
        breakdown = await get_failure_type_breakdown(db)
        for b in sorted(breakdown, key=lambda x: -x.revenue_at_risk):
            print(
                f"  {b.failure_code:25s} "
                f"total={b.total:4d}  "
                f"recovered={b.recovered:4d}  "
                f"rate={b.recovery_rate:5.1f}%  "
                f"₹{float(b.revenue_recovered):>12,.2f}"
            )

    print("\n✅ Demo complete!")
    print(f"\n🌐 Dashboard: http://localhost:5173")
    print(f"📚 API Docs:  http://localhost:8000/docs")
    print(f"🔍 LangSmith: https://smith.langchain.com/")


if __name__ == "__main__":
    asyncio.run(main())
