"""
Settings Configuration Module
Loads environment variables using python-dotenv and provides configuration settings.

AI Provider selection is controlled by AI_PROVIDER:
  - "omniroute"  (default) — routes through OmniRoute to a configured model
  - "groq"       — uses Groq directly (kept for fallback / testing)

Startup validation:
  - If AI_PROVIDER=omniroute and OMNIROUTE_API_KEY is missing → raises ValueError at first LLM call
  - If AI_PROVIDER=groq and GROQ_API_KEY is missing → raises ValueError at first LLM call
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """
    Application settings loaded from environment variables.
    """
    # -----------------------------------------------------------------------
    # AI Provider Selection
    # -----------------------------------------------------------------------
    # Controls which backend LLM provider is used.
    # Accepted values: "omniroute" | "groq"
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "omniroute")

    # -----------------------------------------------------------------------
    # OmniRoute Configuration (default provider)
    # -----------------------------------------------------------------------
    # OmniRoute exposes an OpenAI-compatible API.
    # Obtain your API key and base URL from the OmniRoute dashboard.
    OMNIROUTE_API_KEY: str = os.getenv("OMNIROUTE_API_KEY", "")
    OMNIROUTE_MODEL: str = os.getenv("OMNIROUTE_MODEL", "auto")
    OMNIROUTE_BASE_URL: str = os.getenv("OMNIROUTE_BASE_URL", "http://localhost:20128/v1")

    # -----------------------------------------------------------------------
    # Groq Configuration (kept for fallback / testing)
    # -----------------------------------------------------------------------
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # -----------------------------------------------------------------------
    # Database Configuration
    # -----------------------------------------------------------------------
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./fineanalyst.db")
    ANALYTICS_DATABASE_URL: str = os.getenv("ANALYTICS_DATABASE_URL", "sqlite+aiosqlite:///./analytics.db")

    # -----------------------------------------------------------------------
    # Authentication
    # -----------------------------------------------------------------------
    JWT_SECRET: str = os.getenv("JWT_SECRET", "fineanalyst-dev-secret-change-in-production")

    # -----------------------------------------------------------------------
    # FastAPI Configuration
    # -----------------------------------------------------------------------
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

settings = Settings()
