"""
Settings Configuration Module
Loads environment variables using python-dotenv and provides configuration settings.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """
    Application settings loaded from environment variables.
    """
    # API Keys & LLM Provider Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
    
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./fineanalyst.db")
    ANALYTICS_DATABASE_URL: str = os.getenv("ANALYTICS_DATABASE_URL", "sqlite+aiosqlite:///./analytics.db")
    
    # Authentication
    JWT_SECRET: str = os.getenv("JWT_SECRET", "fineanalyst-dev-secret-change-in-production")
    
    # FastAPI Configuration
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

settings = Settings()
