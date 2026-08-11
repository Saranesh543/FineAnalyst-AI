import asyncio
import sys
import logging

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

from app.services.query_understanding_service import QueryUnderstandingService

async def main():
    service = QueryUnderstandingService()
    tests = [
        "Show me the workflow of an online order from placing the order to delivery. Create a flowchart.",
        "Show the interaction between Customer, Web App, Payment Gateway and Database during checkout.",
        "Show monthly revenue.",
        "Compare revenue and expenses.",
        "Analyze monthly revenue and show the order-processing workflow."
    ]
    
    for t in tests:
        print(f"\n--- TESTING: {t} ---")
        plan = await service.understand(t)
        if plan:
            print(f"Visualization: {plan.requested_visualization}")
            print(f"Requires DB: {plan.requires_database}")
        else:
            print("No plan generated.")

if __name__ == "__main__":
    asyncio.run(main())
