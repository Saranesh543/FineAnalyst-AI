import asyncio
import json
from app.services.analytics_orchestrator import analytics_orchestrator

async def run():
    print("Running orchestrator...")
    res = await analytics_orchestrator.analyze("Show me monthly revenue for Jan-Dec 2025")
    
    print(f"Row count: {res.execution.row_count}")
    print(f"Rows: {res.execution.rows}")
    print(f"SQL: {res.sql}")

if __name__ == "__main__":
    asyncio.run(run())
