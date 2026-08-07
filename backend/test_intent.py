import asyncio
from app.services.intent_router import intent_router

async def test():
    tests = [
        "hi", 
        "hellooo",
        "thnk u",
        "what is our rev?",
        "shw bst sellin prod"
    ]
    for t in tests:
        res = await intent_router.classify(t)
        print(f"[{t}] -> Intent: {res.intent}, Corrected: {res.corrected_message}")

asyncio.run(test())
