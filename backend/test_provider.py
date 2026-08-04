from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GROQ_API_KEY")

print("KEY PREFIX:", key[:8] if key else "None")
print("KEY LENGTH:", len(key) if key else 0)

provider_instance = OpenAIProvider(
    base_url="https://api.groq.com/openai/v1",
    api_key=key,
)

model = OpenAIChatModel(
    model_name="llama-3.3-70b-versatile",
    provider=provider_instance,
)

print(model)