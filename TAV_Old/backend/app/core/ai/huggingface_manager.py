"""
HuggingFace Model Manager

Manages HuggingFace model downloads, caching, and inference.
Supports both local inference and HuggingFace Inference API.

Features:
- Dynamic model loading from 100k+ HuggingFace models
- Local model caching and management
- Automatic model download on first use
- HuggingFace Inference API support (no download needed)
- Task-based model discovery
- Memory-efficient model loading
"""

import logging
import os
import json
import shutil
import asyncio
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class HFTaskType(str, Enum):
    """HuggingFace task types for model categorization"""
    # Natural Language Processing
    TEXT_GENERATION = "text-generation"
    TEXT_CLASSIFICATION = "text-classification"
    TOKEN_CLASSIFICATION = "token-classification"
    QUESTION_ANSWERING = "question-answering"
    TABLE_QUESTION_ANSWERING = "table-question-answering"
    ZERO_SHOT_CLASSIFICATION = "zero-shot-classification"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    FEATURE_EXTRACTION = "feature-extraction"
    FILL_MASK = "fill-mask"
    SENTENCE_SIMILARITY = "sentence-similarity"
    TEXT_RANKING = "text-ranking"
    
    # Computer Vision
    DEPTH_ESTIMATION = "depth-estimation"
    IMAGE_CLASSIFICATION = "image-classification"
    OBJECT_DETECTION = "object-detection"
    IMAGE_SEGMENTATION = "image-segmentation"
    TEXT_TO_IMAGE = "text-to-image"
    IMAGE_TO_TEXT = "image-to-text"
    IMAGE_TO_IMAGE = "image-to-image"
    IMAGE_TO_VIDEO = "image-to-video"
    UNCONDITIONAL_IMAGE_GENERATION = "unconditional-image-generation"
    VIDEO_CLASSIFICATION = "video-classification"
    TEXT_TO_VIDEO = "text-to-video"
    ZERO_SHOT_IMAGE_CLASSIFICATION = "zero-shot-image-classification"
    MASK_GENERATION = "mask-generation"
    ZERO_SHOT_OBJECT_DETECTION = "zero-shot-object-detection"
    TEXT_TO_3D = "text-to-3d"
    IMAGE_TO_3D = "image-to-3d"
    IMAGE_FEATURE_EXTRACTION = "image-feature-extraction"
    KEYPOINT_DETECTION = "keypoint-detection"
    VIDEO_TO_VIDEO = "video-to-video"
    
    # Audio
    TEXT_TO_SPEECH = "text-to-speech"
    TEXT_TO_AUDIO = "text-to-audio"
    AUTOMATIC_SPEECH_RECOGNITION = "automatic-speech-recognition"
    AUDIO_TO_AUDIO = "audio-to-audio"
    AUDIO_CLASSIFICATION = "audio-classification"
    VOICE_ACTIVITY_DETECTION = "voice-activity-detection"
    
    # Multimodal
    AUDIO_TEXT_TO_TEXT = "audio-text-to-text"
    IMAGE_TEXT_TO_TEXT = "image-text-to-text"
    VISUAL_QUESTION_ANSWERING = "visual-question-answering"
    DOCUMENT_QUESTION_ANSWERING = "document-question-answering"
    VIDEO_TEXT_TO_TEXT = "video-text-to-text"
    VISUAL_DOCUMENT_RETRIEVAL = "visual-document-retrieval"
    ANY_TO_ANY = "any-to-any"
    
    # Other
    CONVERSATIONAL = "conversational"


class InferenceMode(str, Enum):
    """Inference execution modes"""
    LOCAL = "local"  # Download and run locally
    API = "api"      # Use HuggingFace Inference API


class HuggingFaceManager:
    """
    Manager for HuggingFace models and inference.
    
    Handles:
    - Model downloads and caching
    - Local inference via transformers
    - API inference via HuggingFace Inference API
    - Model metadata and discovery
    """
    
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        hf_token: Optional[str] = None
    ):
        """
        Initialize HuggingFace Manager.
        
        Args:
            cache_dir: Directory for caching downloaded models (default: data/huggingface_cache)
            hf_token: HuggingFace API token for private models and API inference
        """
        # Set cache directory
        if cache_dir is None:
            # Default to data/huggingface_cache in project root
            project_root = Path(__file__).parent.parent.parent.parent
            cache_dir = project_root / "data" / "huggingface_cache"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # HuggingFace token
        self.hf_token = hf_token or os.getenv("HUGGINGFACE_TOKEN")
        
        # Model registry (tracks downloaded models)
        self.registry_file = self.cache_dir / "model_registry.json"
        self.model_registry = self._load_registry()
        
        # In-memory cache for loaded models (to avoid reloading)
        self._loaded_models: Dict[str, Any] = {}
        
        # Detect available device (GPU if available)
        self.device = self._detect_device()
        
        logger.info(f"🤗 HuggingFace Manager initialized. Cache: {self.cache_dir}, Device: {self.device}")
    
    def _detect_device(self) -> str:
        """
        Detect the best available device for inference.
        
        Returns:
            Device string: "cuda", "mps", or "cpu"
        """
        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                logger.info(f"🎮 GPU detected: {gpu_name}")
                return "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                logger.info(f"🍎 Apple Silicon GPU (MPS) detected")
                return "mps"
            else:
                logger.info(f"💻 No GPU detected, using CPU")
                return "cpu"
        except ImportError:
            logger.warning(f"⚠️ PyTorch not available, defaulting to CPU")
            return "cpu"
    
    def _load_registry(self) -> Dict[str, Any]:
        """Load model registry from disk."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load model registry: {e}")
                return {}
        return {}
    
    def _save_registry(self):
        """Save model registry to disk."""
        try:
            with open(self.registry_file, 'w') as f:
                json.dump(self.model_registry, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save model registry: {e}")
    
    def is_model_cached(self, model_id: str) -> bool:
        """
        Check if a model is already downloaded and cached.
        
        Args:
            model_id: HuggingFace model ID (e.g., "gpt2", "bert-base-uncased")
            
        Returns:
            True if model is cached locally
        """
        return model_id in self.model_registry
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached model information.
        
        Args:
            model_id: HuggingFace model ID
            
        Returns:
            Model metadata dict or None
        """
        return self.model_registry.get(model_id)
    
    def list_cached_models(self) -> List[Dict[str, Any]]:
        """
        List all cached models.
        
        Returns:
            List of model metadata dicts
        """
        return [
            {"model_id": model_id, **info}
            for model_id, info in self.model_registry.items()
        ]
    
    def delete_cached_model(self, model_id: str) -> bool:
        """
        Delete a cached model from disk.
        
        Args:
            model_id: HuggingFace model ID
            
        Returns:
            True if deleted successfully
        """
        if model_id not in self.model_registry:
            logger.warning(f"Model not cached: {model_id}")
            return False
        
        try:
            model_path = self.cache_dir / model_id.replace("/", "_")
            if model_path.exists():
                shutil.rmtree(model_path)
            
            # Remove from registry
            del self.model_registry[model_id]
            self._save_registry()
            
            # Remove from memory cache
            if model_id in self._loaded_models:
                del self._loaded_models[model_id]
            
            logger.info(f"✅ Deleted cached model: {model_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete model {model_id}: {e}")
            return False
    
    async def download_model(
        self,
        model_id: str,
        task: Optional[HFTaskType] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Download a model from HuggingFace Hub.
        
        Args:
            model_id: HuggingFace model ID (e.g., "gpt2", "bert-base-uncased")
            task: Task type (helps with model loading)
            force: Force re-download even if cached
            
        Returns:
            Model metadata dict
            
        Raises:
            Exception if download fails
        """
        if not force and self.is_model_cached(model_id):
            logger.info(f"✅ Model already cached: {model_id}")
            return self.model_registry[model_id]
        
        logger.info(f"📥 Downloading model: {model_id}")
        
        try:
            from huggingface_hub import snapshot_download, model_info
            
            # Get model info from Hub
            info = model_info(model_id, token=self.hf_token)
            
            # Determine task if not provided
            if task is None and hasattr(info, 'pipeline_tag'):
                task = info.pipeline_tag
            
            # Download model files
            model_path = self.cache_dir / model_id.replace("/", "_")
            local_dir = snapshot_download(
                repo_id=model_id,
                cache_dir=str(self.cache_dir),
                local_dir=str(model_path),
                token=self.hf_token
            )
            
            # Store metadata
            # Safely get model size
            size_mb = 0
            if hasattr(info, 'safetensors') and info.safetensors:
                if isinstance(info.safetensors, dict):
                    size_mb = info.safetensors.get('total', 0) / (1024 * 1024)
            
            metadata = {
                "model_id": model_id,
                "task": task,
                "local_path": str(local_dir),
                "downloaded_at": None,  # Will be set by registry
                "model_type": getattr(info, 'model_type', 'unknown'),
                "size_mb": size_mb
            }
            
            # Update registry
            import datetime
            self.model_registry[model_id] = {
                **metadata,
                "downloaded_at": datetime.datetime.utcnow().isoformat()
            }
            self._save_registry()
            
            logger.info(f"✅ Downloaded model: {model_id} -> {local_dir}")
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Failed to download model {model_id}: {e}")
            raise
    
    async def infer_local(
        self,
        model_id: str,
        inputs: Union[str, Dict[str, Any], List[str]],
        task: Optional[HFTaskType] = None,
        model_kwargs: Optional[Dict[str, Any]] = None,
        pipeline_kwargs: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Run local inference using a downloaded model.
        
        Args:
            model_id: HuggingFace model ID
            inputs: Input data (text, image, audio, etc.)
            task: Task type (required if not in registry)
            model_kwargs: Additional kwargs for model (temperature, max_length, etc.)
            pipeline_kwargs: Additional kwargs for pipeline
            
        Returns:
            Inference results
            
        Raises:
            Exception if model not cached or inference fails
        """
        # Check if model is cached
        if not self.is_model_cached(model_id):
            logger.info(f"Model not cached, downloading: {model_id}")
            await self.download_model(model_id, task)
        
        # Get model info
        model_info = self.model_registry[model_id]
        task = task or model_info.get("task")
        
        if not task:
            raise ValueError(f"Task type not specified for model {model_id}")
        
        logger.info(f"🚀 Running local inference: {model_id} (task: {task})")
        
        try:
            # Check if model is already loaded in memory
            cache_key = f"{model_id}:{task}"
            if cache_key not in self._loaded_models:
                from transformers import pipeline
                
                # Load model using transformers pipeline with GPU support
                model_path = model_info["local_path"]
                
                # Set device for pipeline (use GPU if available)
                device = -1 if self.device == "cpu" else 0  # -1 for CPU, 0 for CUDA/MPS
                
                pipe = pipeline(
                    task=task,
                    model=model_path,
                    token=self.hf_token,
                    device=device,
                    **(pipeline_kwargs or {})
                )
                
                self._loaded_models[cache_key] = pipe
                logger.info(f"✅ Loaded model into memory: {model_id} on {self.device}")
            else:
                pipe = self._loaded_models[cache_key]
                logger.debug(f"Using cached model: {model_id}")
            
            # Extract content based on task type
            # Now ALL types use standardized MediaFormat!
            text_based_tasks = [
                HFTaskType.TEXT_GENERATION,
                HFTaskType.TEXT_CLASSIFICATION,
                HFTaskType.TOKEN_CLASSIFICATION,
                HFTaskType.QUESTION_ANSWERING,
                HFTaskType.ZERO_SHOT_CLASSIFICATION,
                HFTaskType.TRANSLATION,
                HFTaskType.SUMMARIZATION,
                HFTaskType.FEATURE_EXTRACTION,
                HFTaskType.FILL_MASK,
                HFTaskType.SENTENCE_SIMILARITY,
            ]
            
            image_based_tasks = [
                HFTaskType.IMAGE_CLASSIFICATION,
                HFTaskType.ZERO_SHOT_IMAGE_CLASSIFICATION,
                HFTaskType.OBJECT_DETECTION,
                HFTaskType.IMAGE_SEGMENTATION,
                HFTaskType.IMAGE_TO_TEXT,
            ]
            
            audio_based_tasks = [
                HFTaskType.AUTOMATIC_SPEECH_RECOGNITION,
                HFTaskType.AUDIO_CLASSIFICATION,
                HFTaskType.TEXT_TO_SPEECH,
                HFTaskType.TEXT_TO_AUDIO,
                HFTaskType.AUDIO_TO_AUDIO,
            ]
            
            processed_inputs = inputs
            
            # Text tasks: Extract text string
            if task in text_based_tasks:
                if isinstance(inputs, dict):
                    from app.core.nodes.multimodal import extract_content
                    processed_inputs = extract_content(inputs)
                    logger.info(f"📝 Extracted text: {processed_inputs[:100] if isinstance(processed_inputs, str) else processed_inputs}")
            
            # Image tasks: Convert to PIL Image
            elif task in image_based_tasks:
                if isinstance(inputs, dict):
                    # NEW: Extract image data using standardized format
                    from app.core.nodes.multimodal import extract_content
                    image_data = extract_content(inputs)  # Gets the "data" field
                    
                    # Check data_type to know how to process
                    if inputs.get("data_type") == "base64":
                        import base64
                        from PIL import Image
                        import io
                        image_bytes = base64.b64decode(image_data)
                        processed_inputs = Image.open(io.BytesIO(image_bytes))
                        logger.info(f"🖼️ Converted base64 to PIL Image: {processed_inputs.size}")
                    elif inputs.get("data_type") == "file_path":
                        from PIL import Image
                        processed_inputs = Image.open(image_data)
                        logger.info(f"🖼️ Loaded PIL Image from path: {processed_inputs.size}")
                    elif inputs.get("data_type") == "url":
                        # Pass URL directly - transformers can handle URLs
                        processed_inputs = image_data
                        logger.info(f"🖼️ Using image URL: {image_data[:100]}")
                    else:
                        # Assume it's already usable
                        processed_inputs = image_data
                        logger.info(f"🖼️ Using image data as-is: {type(image_data)}")
            
            # Audio tasks: Extract audio data
            elif task in audio_based_tasks:
                if isinstance(inputs, dict):
                    from app.core.nodes.multimodal import extract_content
                    audio_data = extract_content(inputs)  # Gets the "data" field
                    
                    # Audio typically needs file path or bytes
                    if inputs.get("data_type") == "file_path":
                        processed_inputs = audio_data
                        logger.info(f"🎵 Using audio file path: {audio_data}")
                    elif inputs.get("data_type") == "base64":
                        # Decode to bytes for transformers
                        import base64
                        audio_bytes = base64.b64decode(audio_data)
                        processed_inputs = audio_bytes
                        logger.info(f"🎵 Decoded audio from base64: {len(audio_bytes)} bytes")
                    else:
                        processed_inputs = audio_data
                        logger.info(f"🎵 Using audio data as-is: {type(audio_data)}")
            
            # Special handling for zero-shot tasks that need candidate_labels as list
            final_kwargs = model_kwargs or {}
            if task in [HFTaskType.ZERO_SHOT_CLASSIFICATION, HFTaskType.ZERO_SHOT_IMAGE_CLASSIFICATION]:
                if 'candidate_labels' in final_kwargs:
                    labels = final_kwargs['candidate_labels']
                    # Convert comma-separated string to list
                    if isinstance(labels, str):
                        final_kwargs['candidate_labels'] = [label.strip() for label in labels.split(',')]
                        logger.info(f"🏷️  Converted candidate_labels to list: {final_kwargs['candidate_labels']}")
            
            # Run inference
            results = pipe(processed_inputs, **final_kwargs)
            
            logger.info(f"✅ Local inference completed: {model_id}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Local inference failed for {model_id}: {e}")
            raise
    
    def _extract_text_content(self, inputs: Union[str, Dict[str, Any], List]) -> str:
        """
        Extract text content from various input formats.
        
        Uses TAV's standardized extract_content utility.
        
        Args:
            inputs: Input in various formats
            
        Returns:
            Extracted text string
        """
        from app.core.nodes.multimodal import extract_content
        return extract_content(inputs)
    
    async def infer_api(
        self,
        model_id: str,
        inputs: Union[str, Dict[str, Any]],
        task: Optional[HFTaskType] = None,
        parameters: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Run inference using HuggingFace Inference API (no download needed).
        
        Args:
            model_id: HuggingFace model ID
            inputs: Input data
            task: Task type (required for API inference)
            parameters: Model parameters (temperature, max_length, etc.)
            options: API options (wait_for_model, use_cache, etc.)
            
        Returns:
            Inference results
            
        Raises:
            Exception if API call fails
        """
        if not self.hf_token:
            raise ValueError("HuggingFace token required for API inference")
        
        if not task:
            raise ValueError("Task type is required for API inference")
        
        logger.info(f"🌐 Running API inference: {model_id} (task: {task})")
        
        try:
            from huggingface_hub import InferenceClient
            
            # Create inference client
            client = InferenceClient(token=self.hf_token, model=model_id)
            
            # Map task to InferenceClient method
            # The InferenceClient has task-specific methods
            task_method_map = {
                # NLP tasks
                HFTaskType.TEXT_GENERATION: "text_generation",
                HFTaskType.TEXT_CLASSIFICATION: "text_classification",
                HFTaskType.TOKEN_CLASSIFICATION: "token_classification",
                HFTaskType.QUESTION_ANSWERING: "question_answering",
                HFTaskType.ZERO_SHOT_CLASSIFICATION: "zero_shot_classification",
                HFTaskType.TRANSLATION: "translation",
                HFTaskType.SUMMARIZATION: "summarization",
                HFTaskType.FEATURE_EXTRACTION: "feature_extraction",
                HFTaskType.FILL_MASK: "fill_mask",
                HFTaskType.SENTENCE_SIMILARITY: "sentence_similarity",
                
                # Computer Vision tasks
                HFTaskType.IMAGE_CLASSIFICATION: "image_classification",
                HFTaskType.OBJECT_DETECTION: "object_detection",
                HFTaskType.IMAGE_SEGMENTATION: "image_segmentation",
                HFTaskType.IMAGE_TO_TEXT: "image_to_text",
                HFTaskType.TEXT_TO_IMAGE: "text_to_image",
                HFTaskType.ZERO_SHOT_IMAGE_CLASSIFICATION: "zero_shot_image_classification",
                
                # Audio tasks
                HFTaskType.AUTOMATIC_SPEECH_RECOGNITION: "automatic_speech_recognition",
                HFTaskType.AUDIO_CLASSIFICATION: "audio_classification",
                HFTaskType.TEXT_TO_SPEECH: "text_to_speech",
                
                # Multimodal
                HFTaskType.VISUAL_QUESTION_ANSWERING: "visual_question_answering",
                HFTaskType.DOCUMENT_QUESTION_ANSWERING: "document_question_answering",
            }
            
            method_name = task_method_map.get(task)
            
            if not method_name:
                # Fallback: use the task value directly and hope it matches
                method_name = task.value.replace("-", "_")
                logger.warning(f"⚠️ Task {task} not in method map, using fallback: {method_name}")
            
            # Get the method from the client
            if not hasattr(client, method_name):
                raise ValueError(
                    f"InferenceClient does not support task '{task}' (method '{method_name}' not found). "
                    f"This task may only be available in Local mode."
                )
            
            method = getattr(client, method_name)
            
            # Call the task-specific method
            # Different methods have different signatures, so we need to handle them appropriately
            logger.info(f"📞 Calling {method_name} on model {model_id}")
            
            # Prepare arguments based on task type
            # Each InferenceClient method has a specific signature
            call_kwargs = {}
            
            if task == HFTaskType.ZERO_SHOT_CLASSIFICATION:
                # zero_shot_classification(text, candidate_labels, multi_label=False, hypothesis_template=None)
                logger.info(f"🔍 Processing zero-shot-classification. Inputs type: {type(inputs)}, Parameters: {parameters}")
                
                # Extract text from TAV's internal format
                text = self._extract_text_content(inputs)
                
                candidate_labels = parameters.get('candidate_labels') if parameters else None
                if not candidate_labels:
                    raise ValueError("zero-shot-classification requires 'candidate_labels' parameter")
                
                # Handle comma-separated string
                if isinstance(candidate_labels, str):
                    candidate_labels = [label.strip() for label in candidate_labels.split(',')]
                
                logger.info(f"📝 Text: {text[:100] if isinstance(text, str) else text}")
                logger.info(f"🏷️  Candidate labels: {candidate_labels}")
                
                call_kwargs = {
                    'candidate_labels': candidate_labels,
                    'multi_label': parameters.get('multi_label', False) if parameters else False
                }
                if parameters and 'hypothesis_template' in parameters:
                    call_kwargs['hypothesis_template'] = parameters['hypothesis_template']
                
                logger.info(f"🚀 Calling zero_shot_classification with text and kwargs: {call_kwargs}")
                
                # Try to call the method, handling different response formats
                try:
                    result = await asyncio.to_thread(method, text, **call_kwargs)
                except (TypeError, KeyError) as e:
                    # If the InferenceClient fails due to unexpected response format,
                    # try calling the raw API directly
                    logger.warning(f"⚠️ InferenceClient failed with {e}, trying direct API call")
                    import httpx
                    async with httpx.AsyncClient(timeout=120.0) as http_client:
                        response = await http_client.post(
                            f"https://api-inference.huggingface.co/models/{model_id}",
                            headers={"Authorization": f"Bearer {self.hf_token}"},
                            json={
                                "inputs": text,
                                "parameters": {
                                    "candidate_labels": candidate_labels,
                                    "multi_label": call_kwargs.get('multi_label', False)
                                }
                            }
                        )
                        response.raise_for_status()
                        result = response.json()
                        logger.info(f"✅ Direct API call succeeded")
            
            elif task == HFTaskType.QUESTION_ANSWERING:
                # question_answering(question, context)
                if isinstance(inputs, dict) and ('question' in inputs or 'context' in inputs):
                    question = inputs.get('question', '')
                    context = self._extract_text_content(inputs.get('context', ''))
                else:
                    # Assume parameters contains question
                    question = parameters.get('question', '') if parameters else ''
                    context = self._extract_text_content(inputs)
                
                result = await asyncio.to_thread(method, question=question, context=context)
            
            elif task == HFTaskType.SENTENCE_SIMILARITY:
                # sentence_similarity(sentence, other_sentences)
                if isinstance(inputs, dict) and 'source_sentence' in inputs:
                    sentence = self._extract_text_content(inputs.get('source_sentence', ''))
                    other_sentences = inputs.get('sentences', [])
                else:
                    sentence = self._extract_text_content(inputs)
                    other_sentences = parameters.get('sentences', []) if parameters else []
                
                # Handle JSON string
                if isinstance(other_sentences, str):
                    import json
                    other_sentences = json.loads(other_sentences)
                
                result = await asyncio.to_thread(method, sentence=sentence, other_sentences=other_sentences)
            
            elif task == HFTaskType.TRANSLATION:
                # translation(text, src_lang=None, tgt_lang=None)
                text = self._extract_text_content(inputs)
                
                call_kwargs = {}
                if parameters:
                    call_kwargs = {k: v for k, v in parameters.items() if k in ['src_lang', 'tgt_lang']}
                
                result = await asyncio.to_thread(method, text, **call_kwargs)
            
            elif task in [HFTaskType.IMAGE_CLASSIFICATION, HFTaskType.OBJECT_DETECTION, 
                          HFTaskType.IMAGE_SEGMENTATION, HFTaskType.IMAGE_TO_TEXT]:
                # Image tasks typically just take the image input
                # inputs should be image bytes or PIL Image
                result = await asyncio.to_thread(method, inputs)
            
            elif task == HFTaskType.VISUAL_QUESTION_ANSWERING:
                # visual_question_answering(image, question)
                if isinstance(inputs, dict):
                    image = inputs.get('image')
                    question = inputs.get('question', '')
                else:
                    image = inputs
                    question = parameters.get('question', '') if parameters else ''
                
                result = await asyncio.to_thread(method, image=image, question=question)
            
            else:
                # Default: pass inputs as first positional arg and parameters as kwargs
                if parameters:
                    call_kwargs.update(parameters)
                result = await asyncio.to_thread(method, inputs, **call_kwargs)
            
            # Log the raw result for debugging
            logger.info(f"📦 API result type: {type(result)}, value preview: {str(result)[:200]}")
            
            logger.info(f"✅ API inference completed: {model_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ API inference failed for {model_id}: {e}")
            # Check if it's a 410 error and provide helpful message
            if "410" in str(e) or "Gone" in str(e):
                raise ValueError(
                    f"Model '{model_id}' is not available on HuggingFace Inference API. "
                    f"This model may require: (1) A paid Inference Endpoint, (2) Local inference mode, "
                    f"or (3) May have been removed from the free tier. "
                    f"Try switching to 'Local' mode to download and run the model on your machine."
                )
            raise
    
    async def infer(
        self,
        model_id: str,
        inputs: Union[str, Dict[str, Any], List[str]],
        mode: InferenceMode = InferenceMode.LOCAL,
        task: Optional[HFTaskType] = None,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        Run inference (automatically selects local or API mode).
        
        Args:
            model_id: HuggingFace model ID
            inputs: Input data
            mode: Inference mode (local or api)
            task: Task type (required for API mode, optional for local)
            parameters: Model parameters
            **kwargs: Additional arguments
            
        Returns:
            Inference results
        """
        if mode == InferenceMode.LOCAL:
            return await self.infer_local(
                model_id=model_id,
                inputs=inputs,
                task=task,
                model_kwargs=parameters,
                **kwargs
            )
        else:
            return await self.infer_api(
                model_id=model_id,
                inputs=inputs,
                task=task,
                parameters=parameters,
                **kwargs
            )
    
    def get_cache_size(self) -> Dict[str, Any]:
        """
        Get total size of cached models.
        
        Returns:
            Cache statistics dict
        """
        total_size = 0
        for model_id, info in self.model_registry.items():
            total_size += info.get("size_mb", 0)
        
        return {
            "total_models": len(self.model_registry),
            "total_size_mb": round(total_size, 2),
            "total_size_gb": round(total_size / 1024, 2),
            "cache_dir": str(self.cache_dir)
        }
    
    def cleanup_old_models(self, keep_recent: int = 10) -> int:
        """
        Delete old cached models, keeping only the most recently used.
        
        Args:
            keep_recent: Number of recent models to keep
            
        Returns:
            Number of models deleted
        """
        if len(self.model_registry) <= keep_recent:
            return 0
        
        # Sort by download date
        sorted_models = sorted(
            self.model_registry.items(),
            key=lambda x: x[1].get("downloaded_at", ""),
            reverse=True
        )
        
        # Delete old models
        deleted_count = 0
        for model_id, _ in sorted_models[keep_recent:]:
            if self.delete_cached_model(model_id):
                deleted_count += 1
        
        logger.info(f"🧹 Cleaned up {deleted_count} old models")
        return deleted_count


# Global instance
_hf_manager: Optional[HuggingFaceManager] = None


def get_huggingface_manager(
    cache_dir: Optional[str] = None,
    hf_token: Optional[str] = None
) -> HuggingFaceManager:
    """
    Get global HuggingFace Manager instance.
    
    Args:
        cache_dir: Cache directory (optional)
        hf_token: HuggingFace token (optional)
        
    Returns:
        HuggingFaceManager instance
    """
    global _hf_manager
    if _hf_manager is None:
        _hf_manager = HuggingFaceManager(cache_dir, hf_token)
    return _hf_manager

