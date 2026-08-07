from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.api.health import router as health_router
from app.api.agent import router as agent_router
from app.api.schema import router as schema_router
from app.api.sql import router as sql_router
from app.api.sql_execute import router as sql_execute_router
from app.api.visualization import router as visualization_router
from app.api.insight import router as insight_router
from app.api.analyze import router as analyze_router
from app.api.debug import router as debug_router
from app.api.auth import router as auth_router
from app.api.sessions import router as sessions_router

api_router = APIRouter()

# Include individual route modules here
api_router.include_router(health_router)
api_router.include_router(auth_router)

# Protected routes
protected_dependencies = [Depends(get_current_user)]

api_router.include_router(agent_router, dependencies=protected_dependencies)
api_router.include_router(schema_router, dependencies=protected_dependencies)
api_router.include_router(sql_router, dependencies=protected_dependencies)
api_router.include_router(sql_execute_router, dependencies=protected_dependencies)
api_router.include_router(visualization_router, dependencies=protected_dependencies)
api_router.include_router(insight_router, dependencies=protected_dependencies)
api_router.include_router(analyze_router, dependencies=protected_dependencies)
api_router.include_router(debug_router, dependencies=protected_dependencies)
api_router.include_router(sessions_router, dependencies=protected_dependencies)
