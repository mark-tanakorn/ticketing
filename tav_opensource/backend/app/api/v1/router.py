"""
API v1 Router
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    workflows,
    executions,
    nodes,
    templates,
    settings,
    files,
    health,
    dashboard,
    ai,
    email_interactions,
    credentials,
    huggingface,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, tags=["Authentication"])
api_router.include_router(users.router, tags=["Users"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
api_router.include_router(executions.router, prefix="/executions", tags=["Executions"])
api_router.include_router(nodes.router, prefix="/nodes", tags=["Nodes"])
api_router.include_router(templates.router, prefix="/templates", tags=["Templates"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI"])
api_router.include_router(files.router, prefix="/files", tags=["Files"])
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(email_interactions.router, prefix="/email-interactions", tags=["Email Interactions"])
api_router.include_router(credentials.router, prefix="/credentials", tags=["Credentials"])
api_router.include_router(huggingface.router, prefix="/huggingface", tags=["HuggingFace"])


