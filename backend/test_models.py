import asyncio
import os
import pydantic_ai
from pydantic_ai import Agent
from app.schemas.intent import IntentResult
from app.services.llm_provider import get_llm_model

models_to_test = [
    "llama-3.1-8b-instant",
    "llama3-groq-8b-8192-tool-use-preview",
    "llama3-groq-70b-8192-tool-use-preview",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
    "llama-3.3-70b-versatile",
]

async def test_model(model_name: str):
    print(f"\nTesting model: {model_name}")
    try:
        os.environ["GROQ_MODEL"] = model_name
        model = get_llm_model()
        agent = Agent(
            model=model,
            output_type=IntentResult,
            system_prompt="Classify the intent of the user into exactly one of three intents: conversation, knowledge, database. Respond strictly with the correct intent.",
        )
        for prompt in ["Hi there!", "What is a primary key?", "Top 5 companies by revenue"]:
            try:
                res = await agent.run(prompt)
                print(f"SUCCESS [{model_name}] '{prompt}': {res.output}")
            except Exception as e:
                print(f"FAILED [{model_name}] '{prompt}': {type(e).__name__} - {e}")
    except Exception as e:
        print(f"FAILED INITIALIZING [{model_name}]: {type(e).__name__} - {e}")

async def main():
    for model in models_to_test:
        await test_model(model)

if __name__ == "__main__":
    asyncio.run(main())
