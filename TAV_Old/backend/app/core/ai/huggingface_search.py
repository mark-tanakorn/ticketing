"""
HuggingFace Model Search and Discovery

Utilities for searching and discovering models from HuggingFace Hub.
"""

import logging
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ModelFilter(str, Enum):
    """Common model filters"""
    TRENDING = "trending"
    MOST_DOWNLOADS = "downloads"
    MOST_LIKES = "likes"
    RECENTLY_UPDATED = "lastModified"


async def search_models(
    query: Optional[str] = None,
    task: Optional[str] = None,
    library: Optional[str] = None,
    language: Optional[str] = None,
    limit: int = 20,
    page: int = 1,
    sort: ModelFilter = ModelFilter.MOST_DOWNLOADS,
    hf_token: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search for models on HuggingFace Hub.
    
    Args:
        query: Search query (model name, description, etc.)
        task: Filter by task (e.g., "text-generation", "image-classification")
        library: Filter by library (e.g., "transformers", "diffusers")
        language: Filter by language (e.g., "en", "zh")
        limit: Maximum number of results per page
        page: Page number (1-indexed)
        sort: Sort order
        hf_token: HuggingFace API token
        
    Returns:
        List of model metadata dicts
    """
    try:
        from huggingface_hub import HfApi
        
        api = HfApi(token=hf_token)
        
        # Calculate limit with offset for pagination
        # HuggingFace API doesn't support offset directly, so we fetch more and slice
        total_to_fetch = limit * page
        
        # Build tags list for filtering
        # HuggingFace uses tags for task filtering, not a separate filter parameter
        tags = []
        if task:
            # Add task as a tag - HuggingFace uses pipeline tags
            tags.append(task)
        if library:
            tags.append(library)
        if language:
            tags.append(language)
        
        logger.info(f"🔍 Searching HuggingFace: query={query}, tags={tags}, sort={sort.value}, limit={total_to_fetch}")
        
        # Search models
        # Note: Don't use filter parameter, use tags instead
        models = api.list_models(
            search=query,
            tags=tags if tags else None,
            sort=sort.value,
            limit=total_to_fetch,
            full=True
        )
        
        # Convert to list and paginate
        all_models = list(models)
        
        logger.info(f"✅ Total models fetched from HF: {len(all_models)}")
        
        # Debug: Log first few models to see what we got
        if all_models:
            logger.info(f"Sample models: {[(m.modelId, getattr(m, 'pipeline_tag', 'NO_TAG')) for m in all_models[:3]]}")
        else:
            logger.warning(f"⚠️ No models found for query={query}, tags={tags}")
        
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_models = all_models[start_idx:end_idx]
        
        logger.info(f"✅ Returning page {page}: {len(paginated_models)} models (indices {start_idx}-{end_idx})")
        
        # Extract relevant info
        results = []
        for model in paginated_models:
            results.append({
                "model_id": model.modelId,
                "author": model.author if hasattr(model, 'author') else None,
                "downloads": model.downloads if hasattr(model, 'downloads') else 0,
                "likes": model.likes if hasattr(model, 'likes') else 0,
                "tags": model.tags if hasattr(model, 'tags') else [],
                "pipeline_tag": model.pipeline_tag if hasattr(model, 'pipeline_tag') else None,
                "library_name": model.library_name if hasattr(model, 'library_name') else None,
                "created_at": model.created_at.isoformat() if hasattr(model, 'created_at') and model.created_at else None,
                "last_modified": model.lastModified.isoformat() if hasattr(model, 'lastModified') and model.lastModified else None,
            })
        
        logger.info(f"✅ Found {len(results)} models (page {page}) for query: {query or 'all'}")
        return results
        
    except Exception as e:
        logger.error(f"❌ Model search failed: {e}", exc_info=True)
        # Return empty list instead of raising to avoid breaking the UI
        return []


async def get_model_card(model_id: str, hf_token: Optional[str] = None) -> Optional[str]:
    """
    Get model card (README) for a model.
    
    Args:
        model_id: HuggingFace model ID
        hf_token: HuggingFace API token
        
    Returns:
        Model card markdown content or None
    """
    try:
        from huggingface_hub import hf_hub_download
        import os
        
        readme_path = hf_hub_download(
            repo_id=model_id,
            filename="README.md",
            token=hf_token,
            repo_type="model"
        )
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
            
    except Exception as e:
        logger.warning(f"Could not fetch model card for {model_id}: {e}")
        return None


async def get_model_info(model_id: str, hf_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific model.
    
    Args:
        model_id: HuggingFace model ID
        hf_token: HuggingFace API token
        
    Returns:
        Model information dict or None
    """
    try:
        from huggingface_hub import HfApi
        
        api = HfApi(token=hf_token)
        model_info = api.model_info(model_id, files_metadata=False)
        
        # Extract relevant info
        result = {
            "model_id": model_info.modelId,
            "name": model_info.modelId.split('/')[-1],
            "author": model_info.author if hasattr(model_info, 'author') else None,
            "downloads": model_info.downloads if hasattr(model_info, 'downloads') else 0,
            "likes": model_info.likes if hasattr(model_info, 'likes') else 0,
            "tags": model_info.tags if hasattr(model_info, 'tags') else [],
            "pipeline_tag": model_info.pipeline_tag if hasattr(model_info, 'pipeline_tag') else None,
            "library_name": model_info.library_name if hasattr(model_info, 'library_name') else None,
            "created_at": model_info.created_at.isoformat() if hasattr(model_info, 'created_at') and model_info.created_at else None,
            "last_modified": model_info.lastModified.isoformat() if hasattr(model_info, 'lastModified') and model_info.lastModified else None,
            "description": getattr(model_info, 'card_data', {}).get('description', '') if hasattr(model_info, 'card_data') else '',
            "private": getattr(model_info, 'private', False),
            "gated": getattr(model_info, 'gated', False),
        }
        
        # Add inference status check
        inference_status = await check_model_inference_status(model_id, hf_token)
        result["inference_status"] = inference_status
        
        logger.info(f"✅ Fetched model info for {model_id}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to get model info for {model_id}: {e}", exc_info=True)
        return None


async def get_popular_models_by_task(
    task: str,
    limit: int = 10,
    hf_token: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get popular models for a specific task.
    
    Args:
        task: Task type (e.g., "text-generation")
        limit: Maximum number of results
        hf_token: HuggingFace API token
        
    Returns:
        List of model metadata dicts
    """
    return await search_models(
        task=task,
        limit=limit,
        sort=ModelFilter.MOST_DOWNLOADS,
        hf_token=hf_token
    )


# Popular model recommendations by task
RECOMMENDED_MODELS = {
    "text-generation": [
        "gpt2",
        "distilgpt2",
        "EleutherAI/gpt-neo-2.7B",
        "facebook/opt-1.3b",
        "meta-llama/Llama-2-7b-hf"  # Requires access
    ],
    "text-classification": [
        "distilbert-base-uncased-finetuned-sst-2-english",
        "bert-base-uncased",
        "roberta-base"
    ],
    "question-answering": [
        "distilbert-base-cased-distilled-squad",
        "bert-large-uncased-whole-word-masking-finetuned-squad"
    ],
    "summarization": [
        "facebook/bart-large-cnn",
        "t5-small",
        "t5-base"
    ],
    "translation": [
        "Helsinki-NLP/opus-mt-en-de",
        "t5-small"
    ],
    "image-classification": [
        "google/vit-base-patch16-224",
        "microsoft/resnet-50"
    ],
    "image-to-text": [
        "Salesforce/blip-image-captioning-base",
        "nlpconnect/vit-gpt2-image-captioning"
    ],
    "text-to-image": [
        "runwayml/stable-diffusion-v1-5",
        "stabilityai/stable-diffusion-2-1"
    ],
    "automatic-speech-recognition": [
        "openai/whisper-small",
        "openai/whisper-base"
    ],
    "feature-extraction": [
        "sentence-transformers/all-MiniLM-L6-v2",
        "sentence-transformers/all-mpnet-base-v2"
    ]
}


def get_recommended_models(task: str) -> List[str]:
    """
    Get recommended models for a task.
    
    Args:
        task: Task type
        
    Returns:
        List of recommended model IDs
    """
    return RECOMMENDED_MODELS.get(task, [])


async def check_model_inference_status(model_id: str, hf_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Check if a model supports inference API.
    
    Args:
        model_id: HuggingFace model ID
        hf_token: Optional HuggingFace token
        
    Returns:
        Dict with inference status information:
        - supports_api: bool - Whether the model likely supports API inference
        - inference_status: str - "available", "unknown", or "unavailable"
        - message: str - Human-readable message
    """
    try:
        from huggingface_hub import HfApi
        api = HfApi(token=hf_token)
        
        model_info = api.get_model_info(model_id)
        
        # Check if model has inference configuration
        # Models with a defined pipeline_tag are more likely to work
        has_pipeline = hasattr(model_info, 'pipeline_tag') and model_info.pipeline_tag is not None
        
        # Check model size - very large models often aren't on free tier
        model_size = None
        if hasattr(model_info, 'safetensors') and model_info.safetensors:
            # Try to get model size from safetensors metadata
            total_size = model_info.safetensors.get('total', 0)
            if total_size:
                model_size = total_size
        
        # Heuristics for API availability
        if not has_pipeline:
            return {
                "supports_api": False,
                "inference_status": "unknown",
                "message": "Model does not specify a pipeline task. API inference may not work. Consider using Local mode."
            }
        
        # Very large models (>10GB) are unlikely to be on free tier
        if model_size and model_size > 10 * 1024 * 1024 * 1024:
            return {
                "supports_api": False,
                "inference_status": "unavailable",
                "message": f"Model is large ({model_size / 1024**3:.1f}GB). API inference likely unavailable on free tier. Use Local mode."
            }
        
        # If we get here, model might work
        return {
            "supports_api": True,
            "inference_status": "available",
            "message": "Model appears to support API inference, but availability is not guaranteed."
        }
        
    except Exception as e:
        logger.warning(f"Could not check inference status for {model_id}: {e}")
        return {
            "supports_api": None,
            "inference_status": "unknown",
            "message": "Unable to determine API support. Try Local mode if API fails."
        }


