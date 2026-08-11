import asyncio
import sys
import logging
import json

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

from app.models.user import User
from app.models.chat import Session
from app.services.analytics_orchestrator import analytics_orchestrator

async def main():
    res = await analytics_orchestrator.analyze(
        question="Show me the workflow of an online order from placing the order to delivery. Create a flowchart.",
        user_id="test",
        session_id="test",
        history=[]
    )
    print(json.dumps(res.model_dump(), indent=2))

if __name__ == "__main__":
    asyncio.run(main())
