"""
HuggingFace API Endpoints

Endpoints for searching and discovering HuggingFace models.
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user_smart
from app.database.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class ModelSearchResult(BaseModel):
    """HuggingFace model search result"""
    model_id: str = Field(..., description="Model ID")
    author: Optional[str] = Field(None, description="Model author/organization")
    downloads: int = Field(0, description="Number of downloads")
    likes: int = Field(0, description="Number of likes")
    tags: List[str] = Field(default_factory=list, description="Model tags")
    pipeline_tag: Optional[str] = Field(None, description="Primary task/pipeline tag")
    library_name: Optional[str] = Field(None, description="Library name (transformers, diffusers, etc.)")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    last_modified: Optional[str] = Field(None, description="Last modification timestamp")


class ModelSearchResponse(BaseModel):
    """Model search response"""
    models: List[ModelSearchResult] = Field(..., description="List of models")
    total: int = Field(..., description="Total number of results")
    query: Optional[str] = Field(None, description="Search query")


class PopularModelsResponse(BaseModel):
    """Popular models by task response"""
    task: str = Field(..., description="Task type")
    models: List[str] = Field(..., description="List of recommended model IDs")


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get(
    "/search",
    response_model=ModelSearchResponse,
    summary="Search HuggingFace models",
    description="Search for models on HuggingFace Hub with filters"
)
async def search_models(
    query: Optional[str] = Query(None, description="Search query"),
    task: Optional[str] = Query(None, description="Filter by task type"),
    library: Optional[str] = Query(None, description="Filter by library (transformers, diffusers, etc.)"),
    language: Optional[str] = Query(None, description="Filter by language (en, es, fr, etc.)"),
    sort: str = Query("downloads", description="Sort by: downloads, likes, trending, lastModified"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Search for models on HuggingFace Hub.
    
    Examples:
    - `/api/v1/huggingface/search?query=gpt2` - Search for GPT-2 models
    - `/api/v1/huggingface/search?task=text-generation&limit=10` - Get top 10 text generation models
    - `/api/v1/huggingface/search?sort=likes&limit=5` - Get top 5 most liked models
    
    Args:
        query: Search query string
        task: Filter by task type
        library: Filter by library
        language: Filter by language
        sort: Sort order
        limit: Maximum results
        current_user: Authenticated user
        
    Returns:
        List of matching models
    """
    try:
        from app.core.ai.huggingface_search import search_models as search_hf_models, ModelFilter
        
        # Convert sort string to enum
        try:
            sort_filter = ModelFilter(sort)
        except ValueError:
            sort_filter = ModelFilter.MOST_DOWNLOADS
        
        # Search models
        models = await search_hf_models(
            query=query,
            task=task,
            library=library,
            language=language,
            limit=limit,
            page=page,
            sort=sort_filter
        )
        
        logger.info(f"User {current_user.id} searched HuggingFace models: query={query}, task={task}, found={len(models)}")
        
        return ModelSearchResponse(
            models=[ModelSearchResult(**m) for m in models],
            total=len(models),
            query=query
        )
        
    except Exception as e:
        logger.error(f"Error searching HuggingFace models: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search models: {str(e)}"
        )


@router.get(
    "/popular/{task}",
    response_model=PopularModelsResponse,
    summary="Get popular models by task",
    description="Get recommended popular models for a specific task"
)
async def get_popular_models(
    task: str,
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Get popular/recommended models for a specific task.
    
    Examples:
    - `/api/v1/huggingface/popular/text-generation` - Get popular text generation models
    - `/api/v1/huggingface/popular/image-classification` - Get popular image classification models
    
    Args:
        task: Task type
        limit: Maximum number of models to return
        current_user: Authenticated user
        
    Returns:
        List of popular model IDs for the task
    """
    try:
        from app.core.ai.huggingface_search import get_popular_models_by_task
        
        models = await get_popular_models_by_task(
            task=task,
            limit=limit
        )
        
        model_ids = [m["model_id"] for m in models]
        
        logger.info(f"User {current_user.id} requested popular models for task: {task}, found={len(model_ids)}")
        
        return PopularModelsResponse(
            task=task,
            models=model_ids
        )
        
    except Exception as e:
        logger.error(f"Error getting popular models for task {task}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get popular models: {str(e)}"
        )


@router.get(
    "/recommended/{task}",
    response_model=PopularModelsResponse,
    summary="Get recommended models by task",
    description="Get curated recommended models for a specific task"
)
async def get_recommended_models(
    task: str,
    current_user: User = Depends(get_current_user_smart)
):
    """
    Get curated recommended models for a specific task.
    
    Examples:
    - `/api/v1/huggingface/recommended/text-generation` - Get recommended text generation models
    - `/api/v1/huggingface/recommended/image-classification` - Get recommended image classification models
    
    Args:
        task: Task type
        current_user: Authenticated user
        
    Returns:
        List of recommended model IDs for the task
    """
    try:
        from app.core.ai.huggingface_search import get_recommended_models as get_rec_models
        
        model_ids = get_rec_models(task)
        
        logger.info(f"User {current_user.id} requested recommended models for task: {task}, found={len(model_ids)}")
        
        return PopularModelsResponse(
            task=task,
            models=model_ids
        )
        
    except Exception as e:
        logger.error(f"Error getting recommended models for task {task}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommended models: {str(e)}"
        )


@router.get(
    "/model/{model_id:path}/info",
    summary="Get model details",
    description="Get detailed information about a specific model"
)
async def get_model_details(
    model_id: str,
    current_user: User = Depends(get_current_user_smart)
):
    """
    Get detailed information about a specific HuggingFace model.
    
    Examples:
    - `/api/v1/huggingface/model/gpt2/info` - Get details for GPT-2 model
    - `/api/v1/huggingface/model/bert-base-uncased/info` - Get details for BERT model
    
    Args:
        model_id: HuggingFace model ID (e.g., "gpt2", "bert-base-uncased")
        current_user: Authenticated user
        
    Returns:
        Detailed model information including metadata, tags, and stats
    """
    try:
        from app.core.ai.huggingface_search import get_model_info
        
        model_info = await get_model_info(model_id)
        
        if not model_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model '{model_id}' not found"
            )
        
        logger.info(f"User {current_user.id} requested details for model: {model_id}")
        
        return model_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching model details for {model_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch model details: {str(e)}"
        )


@router.get(
    "/model/{model_id:path}/card",
    summary="Get model card",
    description="Get the model card (README) for a specific model"
)
async def get_model_card(
    model_id: str,
    current_user: User = Depends(get_current_user_smart)
):
    """
    Get the model card (README) for a specific HuggingFace model.
    
    Args:
        model_id: HuggingFace model ID
        current_user: Authenticated user
        
    Returns:
        Model card content in Markdown format
    """
    try:
        from app.core.ai.huggingface_search import get_model_card as fetch_card
        
        card_content = await fetch_card(model_id)
        
        if not card_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model card for '{model_id}' not found"
            )
        
        logger.info(f"User {current_user.id} requested model card for: {model_id}")
        
        return {
            "model_id": model_id,
            "content": card_content
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching model card for {model_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch model card: {str(e)}"
        )


@router.get(
    "/tasks",
    summary="List available tasks",
    description="Get list of all available HuggingFace tasks"
)
async def list_tasks(
    current_user: User = Depends(get_current_user_smart)
):
    """
    Get list of all available HuggingFace task types.
    
    Returns:
        List of task types with descriptions
    """
    from app.core.ai.huggingface_manager import HFTaskType
    
    tasks = [
        {
            "value": task.value,
            "label": task.value.replace("-", " ").title(),
            "category": _get_task_category(task.value)
        }
        for task in HFTaskType
    ]
    
    return {"tasks": tasks}


@router.get(
    "/task-config/{task}",
    summary="Get task-specific configuration schema",
    description="Get configuration schema for a specific HuggingFace task"
)
async def get_task_config_schema(
    task: str,
    current_user: User = Depends(get_current_user_smart)
):
    """
    Get configuration schema for a specific HuggingFace task.
    This returns the relevant parameters that should be shown for the selected task.
    
    Examples:
    - `/api/v1/huggingface/task-config/text-generation` - Get config for text generation
    - `/api/v1/huggingface/task-config/image-classification` - Get config for image classification
    
    Args:
        task: Task type (e.g., "text-generation", "image-classification")
        current_user: Authenticated user
        
    Returns:
        Configuration schema for the task
    """
    try:
        # Get the task-specific parameters from the HuggingFace node
        from app.core.nodes.builtin.ai.huggingface import HuggingFaceNode
        
        full_schema = HuggingFaceNode.get_config_schema()
        
        # Extract common parameters and task-specific schemas
        common_params = full_schema.get("common_parameters", {}).get("properties", {})
        task_schemas = full_schema.get("task_specific_parameters", {}).get("schemas", {})
        
        logger.info(f"📋 Schema analysis: common_params={len(common_params)}, task_schemas={len(task_schemas)}, looking for task={task}")
        
        # Filter parameters based on task
        relevant_params = {}
        
        # Add common parameters that are applicable to this task
        for param_name, param_config in common_params.items():
            applicable_tasks = param_config.get("applicable_tasks", [])
            # If no applicable_tasks specified, show for all tasks
            # If applicable_tasks is specified, only show if task matches
            if not applicable_tasks or task in applicable_tasks:
                relevant_params[param_name] = param_config
                logger.debug(f"  ✓ Added common param: {param_name} (applicable_tasks: {applicable_tasks or 'all'})")
            else:
                logger.debug(f"  ✗ Skipped common param: {param_name} (not applicable to {task})")
        
        # Add task-specific parameters from schemas
        if task in task_schemas:
            task_specific_params = task_schemas[task]
            logger.info(f"  ✅ Found task-specific schema for {task} with {len(task_specific_params)} parameters")
            for param_name, param_config in task_specific_params.items():
                relevant_params[param_name] = param_config
                logger.debug(f"  ✓ Added task-specific param: {param_name}")
        else:
            logger.warning(f"  ⚠️ No task-specific schema found for {task}")
        
        logger.info(f"✅ User {current_user.id} requested task config for: {task}, returning {len(relevant_params)} parameters")
        
        # If no parameters matched, return at least the common ones that have no restrictions
        if len(relevant_params) == 0:
            logger.warning(f"⚠️ No parameters found for task {task}, falling back to all common parameters")
            relevant_params = {k: v for k, v in common_params.items() if not v.get("applicable_tasks")}
        
        return {
            "task": task,
            "parameters": relevant_params
        }
        
    except Exception as e:
        logger.error(f"Error getting task config for {task}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task configuration: {str(e)}"
        )


def _get_task_category(task: str) -> str:
    """Categorize task types"""
    # Natural Language Processing
    if task in [
        "text-generation", "text-classification", "token-classification", 
        "question-answering", "table-question-answering", "zero-shot-classification",
        "translation", "summarization", "feature-extraction", "fill-mask",
        "sentence-similarity", "text-ranking"
    ]:
        return "Natural Language Processing"
    
    # Computer Vision
    elif task in [
        "depth-estimation", "image-classification", "object-detection", 
        "image-segmentation", "text-to-image", "image-to-text", "image-to-image",
        "image-to-video", "unconditional-image-generation", "video-classification",
        "text-to-video", "zero-shot-image-classification", "mask-generation",
        "zero-shot-object-detection", "text-to-3d", "image-to-3d",
        "image-feature-extraction", "keypoint-detection", "video-to-video"
    ]:
        return "Computer Vision"
    
    # Audio
    elif task in [
        "text-to-speech", "text-to-audio", "automatic-speech-recognition",
        "audio-to-audio", "audio-classification", "voice-activity-detection"
    ]:
        return "Audio"
    
    # Multimodal
    elif task in [
        "audio-text-to-text", "image-text-to-text", "visual-question-answering",
        "document-question-answering", "video-text-to-text", 
        "visual-document-retrieval", "any-to-any"
    ]:
        return "Multimodal"
    
    # Other
    else:
        return "Other"
