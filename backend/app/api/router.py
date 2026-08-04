"""
Main API Router Module
Aggregates all API routes into a single router.
"""
from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.agent import router as agent_router
from app.api.schema import router as schema_router
from app.api.sql import router as sql_router
from app.api.sql_execute import router as sql_execute_router
from app.api.visualization import router as visualization_router
from app.api.insight import router as insight_router
from app.api.analyze import router as analyze_router

api_router = APIRouter()

# Include individual route modules here
api_router.include_router(health_router)
api_router.include_router(agent_router)
api_router.include_router(schema_router)
api_router.include_router(sql_router)
api_router.include_router(sql_execute_router)
api_router.include_router(visualization_router)
api_router.include_router(insight_router)
api_router.include_router(analyze_router)

