import asyncio
import traceback
from app.services.agent_service import agent_service

async def main():
    try:
        await agent_service.process_message("Show me total sales", session_id="test-session-123")
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
