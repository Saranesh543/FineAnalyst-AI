# FineAnalyst AI - Backend Foundation

This is the foundational backend for the FineAnalyst AI project. 
It provides a production-ready setup utilizing FastAPI, SQLAlchemy, and SQLite.

## Tech Stack
- **Python:** 3.14+
- **Framework:** FastAPI
- **Database:** SQLite with SQLAlchemy (Async)
- **Configuration:** python-dotenv
- **AI Tooling (Dependencies installed):** Pydantic AI, Google Gemini SDK, Plotly

## Folder Structure
- `app/api/`: API routers and endpoints
- `app/agents/`: AI agent implementations
- `app/config/`: Configuration and settings loading
- `app/database/`: Database connection and session management
- `app/models/`: SQLAlchemy ORM models
- `app/services/`: Business logic layer
- `app/tools/`: Custom tools for AI agents
- `app/utils/`: Utility functions and global exception handlers
- `app/schemas/`: Pydantic schemas for data validation
- `app/prompts/`: Prompt templates for AI models
- `app/main.py`: FastAPI application entry point

## Setup Instructions

1. Clone the repository and navigate to the backend directory.
2. Create and activate a virtual environment.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your configuration:
   ```bash
   cp .env.example .env
   ```
5. Run the application:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Endpoints
- `GET /api/v1/health`: Health check endpoint.
