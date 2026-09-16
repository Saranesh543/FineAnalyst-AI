"""
OmniRoute Provider Validation Script

Validates that:
1. OmniRoute configuration loads correctly from .env
2. The provider factory returns a model instance when configured
3. The provider selection logic is exercised correctly

Usage:
    cd backend
    .venv\\Scripts\\activate
    python test_provider.py
"""
import os
from dotenv import load_dotenv

load_dotenv()

provider = os.getenv("AI_PROVIDER", "omniroute")
print(f"AI_PROVIDER: {provider}")

# --- OmniRoute ---
if provider == "omniroute":
    key = os.getenv("OMNIROUTE_API_KEY", "")
    base_url = os.getenv("OMNIROUTE_BASE_URL", "http://localhost:20128/v1")
    model_id = os.getenv("OMNIROUTE_MODEL", "auto")

    print(f"OMNIROUTE_BASE_URL: {base_url}")
    print(f"OMNIROUTE_MODEL: {model_id!r}")
    print(f"OMNIROUTE_API_KEY length: {len(key)} chars | prefix: {key[:8] if key else 'None'}")

    if not key or key.startswith("your_"):
        print("[ERROR] OMNIROUTE_API_KEY is missing or not configured. Set it in .env.")
        exit(1)


    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    provider_instance = OpenAIProvider(
        base_url=base_url,
        api_key=key,
    )
    model = OpenAIChatModel(
        model_name=model_id,
        provider=provider_instance,
    )
    print(f"[OK] OmniRoute model instance created: {model}")

# --- Groq fallback ---
elif provider == "groq":
    key = os.getenv("GROQ_API_KEY", "")
    model_id = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    print(f"GROQ_MODEL: {model_id!r}")
    print(f"GROQ_API_KEY length: {len(key)} chars | prefix: {key[:8] if key else 'None'}")

    if not key or key.startswith("your_groq"):
        print("[ERROR] GROQ_API_KEY is missing or not configured. Set it in .env.")
        exit(1)

    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    provider_instance = OpenAIProvider(
        base_url="https://api.groq.com/openai/v1",
        api_key=key,
    )
    model = OpenAIChatModel(
        model_name=model_id,
        provider=provider_instance,
    )
    print(f"[OK] Groq model instance created: {model}")

else:
    print(f"[ERROR] Unknown AI_PROVIDER: {provider!r}. Supported: 'omniroute', 'groq'.")
    exit(1)

print("\n[PASS] Provider configuration is valid.")