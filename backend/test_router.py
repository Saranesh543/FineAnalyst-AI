import asyncio
import logging
from app.services.intent_router import intent_router

logging.basicConfig(level=logging.DEBUG)

async def main():
    message = 'Previous context from conversation history: []. New question: "Can you give me top 5 countries by net revenue". Please answer the new question fully incorporating the previous context where relevant.'
    try:
        res = await intent_router.classify(message)
        print("SUCCESS:", res)
    except Exception as e:
        print("EXCEPTION:", type(e), e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
