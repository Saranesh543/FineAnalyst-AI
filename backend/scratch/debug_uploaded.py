import asyncio
import os
import sqlite3
import pandas as pd

# Fix imports
from app.models.user import User
from app.models.chat import Session

from app.services.analytics_orchestrator import analytics_orchestrator

async def run():
    user_id = 999
    db_path = f"analytics_user_{user_id}.db"
    
    data = {
        "Month": ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06", "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12"],
        "Revenue": [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200]
    }
    df = pd.DataFrame(data)
    
    conn = sqlite3.connect(db_path)
    df.to_sql("uploaded_file", conn, if_exists="replace", index=False)
    conn.close()

    print("Running orchestrator...")
    res = await analytics_orchestrator.analyze(
        question="Show me monthly revenue",
        user_id=user_id,
        session_id="mock"
    )
    
    print(f"Row count: {res.execution.row_count}")
    print(f"Rows: {res.execution.rows}")
    print(f"SQL: {res.sql}")
    
    if os.path.exists(db_path):
        os.remove(db_path)

if __name__ == "__main__":
    asyncio.run(run())
