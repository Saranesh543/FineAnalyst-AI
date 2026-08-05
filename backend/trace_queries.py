import asyncio
from app.services.analytics_orchestrator import analytics_orchestrator
from app.schemas.analyze import AnalyzeRequest
import logging

logging.basicConfig(level=logging.INFO)

async def trace_query(question):
    print(f"\n{'='*80}\nTracing: {question}\n{'='*80}")
    try:
        response = await analytics_orchestrator.analyze(
            question=question
        )
        print("Success! SQL Generated:")
        print(response.sql)
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

async def main():
    queries = [
        "Show total revenue",
        "Top 5 companies by revenue",
        "Revenue share by category",
        "Monthly revenue",
        "Show all orders",
        "Top 10 customers",
        "Average order value",
        "Orders by month",
        "Revenue by region"
    ]
    for q in queries:
        await trace_query(q)

if __name__ == "__main__":
    asyncio.run(main())
