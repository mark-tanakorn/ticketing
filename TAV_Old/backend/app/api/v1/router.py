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
    sso,
    dev_tools,

)

api_router = APIRouter()

# Include all endpoint routers
# Note: Tags are defined in each endpoint file, not here
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(workflows.router, prefix="/workflows")
api_router.include_router(executions.router, prefix="/executions")
api_router.include_router(nodes.router, prefix="/nodes")
api_router.include_router(templates.router, prefix="/templates")
api_router.include_router(settings.router, prefix="/settings")
api_router.include_router(ai.router, prefix="/ai")
api_router.include_router(files.router, prefix="/files")
api_router.include_router(health.router, prefix="/health")
api_router.include_router(dashboard.router, prefix="/dashboard")
api_router.include_router(email_interactions.router, prefix="/email-interactions")
api_router.include_router(credentials.router, prefix="/credentials")
api_router.include_router(huggingface.router, prefix="/huggingface")
api_router.include_router(sso.router)
api_router.include_router(dev_tools.router)

