import asyncio
import logging
from app.services.agent_service import agent_service

# Configure full traceback logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

async def test_agent():
    print("\n--- TEST: hi ---")
    res1 = await agent_service.process_message("hi", session_id="test-session")
    print("Response 1:", res1)
    
    print("\n--- TEST: do u know the meaning of wtf ---")
    res2 = await agent_service.process_message("do u know the meaning of wtf", session_id="test-session")
    print("Response 2:", res2)

if __name__ == "__main__":
    asyncio.run(test_agent())
