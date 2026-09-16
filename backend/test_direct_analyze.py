import asyncio
import logging
from app.services.analytics_orchestrator import analytics_orchestrator
from app.schemas.intent import AnalyzeRequest

# Configure full traceback logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

async def test_analyze():
    print("\n--- TEST: do u know the meaning of wtf ---")
    req = AnalyzeRequest(question="do u know the meaning of wtf", history=[])
    res = await analytics_orchestrator.analyze(req, request_id="test-123")
    print("Response:", res)

if __name__ == "__main__":
    asyncio.run(test_analyze())
