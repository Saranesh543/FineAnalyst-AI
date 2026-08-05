import json
from app.main import app
from fastapi.openapi.utils import get_openapi

openapi_schema = get_openapi(
    title="test",
    version="1",
    routes=app.routes
)
paths = list(openapi_schema["paths"].keys())
print("ROUTES:", paths)
