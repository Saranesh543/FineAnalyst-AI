import asyncio
import sys
import logging

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

from app.models.user import User
from app.models.chat import Session
from app.models.chat import Session, MessageTurn, Role

from app.services.analytics_orchestrator import analytics_orchestrator

async def main():
    try:
        response = await analytics_orchestrator.analyze(
            MessageTurn(role=Role.USER, content="Show me the workflow of an online order from placing the order to delivery. Create a flowchart."),
            user_id="test-user",
            session_id="test-session",
            history=[]
        )
        print("SUCCESS:", response.model_dump_json(indent=2))
    except Exception as e:
        print("FAILED:", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
