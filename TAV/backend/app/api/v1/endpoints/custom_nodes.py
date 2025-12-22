"""
Custom Nodes API router (composed).

This file is intentionally small: it composes sub-routers for:
- chat/conversations
- tooling (read-only lookup + examples)
- user library (My Nodes)

External API paths remain unchanged because api/v1/router.py includes this router
under the `/custom-nodes` prefix.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.custom_nodes_chat import router as chat_router
from app.api.v1.endpoints.custom_nodes_library import router as library_router
from app.api.v1.endpoints.custom_nodes_tools import router as tools_router

router = APIRouter()
router.include_router(tools_router)
router.include_router(chat_router)
router.include_router(library_router)


