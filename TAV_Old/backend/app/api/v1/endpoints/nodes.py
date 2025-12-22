"""
Node Definitions API Endpoints

Provides node type information for the workflow editor.
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from app.core.nodes.registry import NodeRegistry
from app.core.nodes.loader import discover_and_register_nodes
from app.schemas.workflow import NodeCategory

logger = logging.getLogger(__name__)

router = APIRouter()


# Response Models
class NodeDefinition(BaseModel):
    """Node definition for frontend"""
    node_type: str
    display_name: str
    description: str
    category: Optional[str]
    icon: Optional[str]
    input_ports: List[Dict[str, Any]]
    output_ports: List[Dict[str, Any]]
    config_schema: Dict[str, Any]
    class_name: str


class NodeDefinitionsResponse(BaseModel):
    """Response model for node definitions endpoint"""
    success: bool
    nodes: List[NodeDefinition]
    categories: Dict[str, List[NodeDefinition]]
    registry_info: Dict[str, Any]
    total_nodes: int


class NodeRegistryStatusResponse(BaseModel):
    """Response model for registry status"""
    success: bool
    total_nodes: int
    nodes_by_category: Dict[str, int]
    node_types: List[str]


# Endpoints

@router.get("/definitions", response_model=NodeDefinitionsResponse)
async def get_node_definitions(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in name or description")
):
    """
    Get all available node definitions for the workflow editor.
    
    This endpoint provides complete node metadata including:
    - Display information (name, description, icon)
    - Port definitions (inputs/outputs)
    - Configuration schema
    - Category information
    
    Used by the frontend to populate the node sidebar and configure nodes.
    
    Query Parameters:
    - category: Filter nodes by category (e.g., "ai", "actions", "triggers")
    - search: Search nodes by name or description
    
    Returns:
    - nodes: List of all node definitions
    - categories: Nodes grouped by category
    - registry_info: Registry statistics
    """
    logger.info(f"📋 Fetching node definitions (category={category}, search={search})")
    
    try:
        # Get all nodes with full details
        all_nodes = NodeRegistry.list_all_with_details()
        
        logger.info(f"Found {len(all_nodes)} registered nodes")
        
        # Build node definitions
        node_definitions = []
        for node_type, metadata in all_nodes.items():
            # Apply category filter
            if category and metadata.get("category") != category:
                continue
            
            # Apply search filter
            if search:
                search_lower = search.lower()
                if (search_lower not in metadata.get("display_name", "").lower() and
                    search_lower not in metadata.get("description", "").lower()):
                    continue
            
            node_def = NodeDefinition(
                node_type=node_type,
                display_name=metadata.get("display_name", node_type),
                description=metadata.get("description", ""),
                category=metadata.get("category"),
                icon=metadata.get("icon"),
                input_ports=metadata.get("input_ports", []),
                output_ports=metadata.get("output_ports", []),
                config_schema=metadata.get("config_schema", {}),
                class_name=metadata.get("class_name", "")
            )
            node_definitions.append(node_def)
        
        # Group by category
        categories = {}
        for node_def in node_definitions:
            cat = node_def.category or "uncategorized"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(node_def)
        
        # Registry info
        registry_info = {
            "total_categories": len(categories),
            "available_categories": list(categories.keys()),
            "nodes_per_category": {cat: len(nodes) for cat, nodes in categories.items()}
        }
        
        logger.info(
            f"✅ Returning {len(node_definitions)} nodes in {len(categories)} categories"
        )
        
        return NodeDefinitionsResponse(
            success=True,
            nodes=node_definitions,
            categories=categories,
            registry_info=registry_info,
            total_nodes=len(node_definitions)
        )
    
    except Exception as e:
        logger.error(f"❌ Error fetching node definitions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch node definitions: {str(e)}"
        )


@router.get("/registry/status", response_model=NodeRegistryStatusResponse)
async def get_registry_status():
    """
    Get node registry status and statistics.
    
    Returns information about registered nodes without fetching full metadata.
    Useful for health checks and debugging.
    
    Returns:
    - total_nodes: Total number of registered nodes
    - nodes_by_category: Count of nodes per category
    - node_types: List of all registered node types
    """
    logger.info("📊 Fetching registry status")
    
    try:
        all_nodes = NodeRegistry.list_all()
        
        # Count nodes by category
        nodes_by_category = {}
        for node_type, metadata in all_nodes.items():
            category = metadata.get("category") or "uncategorized"
            nodes_by_category[category] = nodes_by_category.get(category, 0) + 1
        
        return NodeRegistryStatusResponse(
            success=True,
            total_nodes=len(all_nodes),
            nodes_by_category=nodes_by_category,
            node_types=list(all_nodes.keys())
        )
    
    except Exception as e:
        logger.error(f"❌ Error fetching registry status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch registry status: {str(e)}"
        )


@router.post("/registry/reload")
async def reload_node_registry():
    """
    Reload node registry (development endpoint).
    
    Force re-discovery and re-registration of all nodes.
    Useful during development when adding new nodes.
    
    WARNING: This clears the registry and re-scans all modules.
    Should only be used in development environments.
    
    Returns:
    - Discovery statistics
    """
    logger.info("🔄 Reloading node registry...")
    
    try:
        # Clear existing registry
        NodeRegistry.clear()
        
        # Re-discover nodes
        stats = discover_and_register_nodes()
        
        logger.info(f"✅ Registry reloaded: {stats}")
        
        return {
            "success": True,
            "message": "Node registry reloaded successfully",
            "stats": stats
        }
    
    except Exception as e:
        logger.error(f"❌ Error reloading registry: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reload registry: {str(e)}"
        )


@router.get("/categories")
async def get_node_categories():
    """
    Get all available node categories.
    
    Returns list of categories with counts.
    Useful for building category filters in the UI.
    
    Returns:
    - categories: List of category names
    - counts: Number of nodes per category
    """
    logger.info("📑 Fetching node categories")
    
    try:
        all_nodes = NodeRegistry.list_all()
        
        # Count nodes by category
        category_counts = {}
        for node_type, metadata in all_nodes.items():
            category = metadata.get("category") or "uncategorized"
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Get all possible categories from enum
        all_categories = [cat.value for cat in NodeCategory]
        
        return {
            "success": True,
            "categories": all_categories,
            "registered_categories": list(category_counts.keys()),
            "counts": category_counts,
            "total_categories": len(category_counts)
        }
    
    except Exception as e:
        logger.error(f"❌ Error fetching categories: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch categories: {str(e)}"
        )

