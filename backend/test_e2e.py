import asyncio
import json
from app.services.analytics_orchestrator import analytics_orchestrator

async def test_end_to_end():
    question = "Top 5 companies by revenue"
    print(f"QUERYING: {question}\n" + "="*50)
    try:
        response = await analytics_orchestrator.analyze(question)
        print("SQL EXECUTED:")
        print(response.sql)
        print("\nINSIGHT SUMMARY:")
        if response.insight:
            print(response.insight.summary)
            print("KEY FINDINGS:")
            for kf in response.insight.key_findings:
                print(f"- {kf}")
        print("="*50)
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_end_to_end())
