"""
HuggingFace Inference Node

A marketplace-style node for running inference with 100k+ HuggingFace models.
Supports both local execution (download + run) and API execution (no download).

Features:
- Model marketplace search UI
- Dynamic configuration based on task type
- Credential manager integration for API keys
- Local and API inference modes
- Automatic model downloading and caching
"""

import logging
from typing import Dict, Any, List, Optional
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="huggingface_inference",
    category=NodeCategory.AI,
    name="HuggingFace Model",
    description="Run inference with any HuggingFace model - repository of models available for text, image, audio, and more",
    icon="fa-solid fa-face-smile",
    version="1.0.0"
)
class HuggingFaceNode(Node):
    """
    HuggingFace Inference Node - Universal model marketplace.
    
    This node provides access to HuggingFace's entire model ecosystem:
    - Text generation, classification, summarization, translation
    - Image generation, classification, segmentation
    - Audio transcription, generation
    - Embeddings and feature extraction
    - And much more!
    
    Modes:
    - **Local**: Download model and run locally (privacy-first, no API calls after download)
    - **API**: Use HuggingFace Inference API (no download, faster for occasional use)
    
    The configuration is dynamic - it adapts based on the task type of the selected model.
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "input",
                "type": PortType.UNIVERSAL,
                "display_name": "Input",
                "description": "Input data (text, image, audio, etc. - depends on model task)",
                "required": True
            },
            {
                "name": "parameters",
                "type": PortType.UNIVERSAL,
                "display_name": "Parameters",
                "description": "Additional model parameters (optional, overrides config)",
                "required": False
            }
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "output",
                "type": PortType.UNIVERSAL,
                "display_name": "Output",
                "description": "Model output (format depends on task type)"
            },
            {
                "name": "metadata",
                "type": PortType.UNIVERSAL,
                "display_name": "Metadata",
                "description": "Execution metadata (model info, timing, mode, etc.)"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """
        Define configuration schema with marketplace-style model selection.
        
        This schema includes:
        1. Model marketplace search
        2. Inference mode selection (local vs API)
        3. Credential selection for API mode
        4. Dynamic task-specific parameters
        """
        return {
            # ============= MODEL MARKETPLACE =============
            "huggingface_marketplace": {
                "type": "object",
                "label": "HuggingFace Model",
                "description": "Search and select from 100k+ HuggingFace models",
                "widget": "huggingface_model_browser",  # Custom widget for marketplace UI
                "required": True,
            },
            
            # ============= INFERENCE MODE =============
            "inference_mode": {
                "type": "string",
                "label": "Inference Mode",
                "description": "How to run the model",
                "required": True,
                "default": "local",
                "widget": "select",
                "options": [
                    {
                        "value": "local",
                        "label": "🖥️ Local (Download & Run)",
                        "description": "Download model and run locally. Privacy-first, no API calls after download. Better for repeated use."
                    },
                    {
                        "value": "api",
                        "label": "🌐 API (HuggingFace Inference API)",
                        "description": "Use HuggingFace Inference API. No download needed. Better for occasional use or large models."
                    }
                ],
                "help_text": "Local mode downloads the model once and runs it on your machine. API mode requires HuggingFace API credentials."
            },
            
            # ============= CREDENTIALS (for API mode) =============
            "credential_id": {
                "type": "integer",
                "label": "HuggingFace API Credential",
                "description": "Select your HuggingFace API credential (required for API mode)",
                "required": False,
                "widget": "credential"
            },
            
            # ============= COMMON PARAMETERS =============
            # Note: These are defined here for backend validation but rendered dynamically on frontend
            "common_parameters": {
                "type": "object",
                "label": "Common Parameters",
                "description": "Parameters that work across most models",
                "widget": "hidden",  # Hide from UI - rendered dynamically based on task
                "properties": {
                    "max_length": {
                        "type": "integer",
                        "label": "Max Length",
                        "description": "Maximum length of generated output (for generation tasks)",
                        "required": False,
                        "default": 100,
                        "min": 1,
                        "max": 2048,
                        "widget": "number",
                        "applicable_tasks": ["text-generation", "summarization", "translation"]
                    },
                    "temperature": {
                        "type": "number",
                        "label": "Temperature",
                        "description": "Sampling temperature (higher = more creative, lower = more deterministic)",
                        "required": False,
                        "default": 1.0,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.1,
                        "widget": "slider",
                        "applicable_tasks": ["text-generation", "conversational"]
                    },
                    "top_p": {
                        "type": "number",
                        "label": "Top P",
                        "description": "Nucleus sampling threshold",
                        "required": False,
                        "default": 1.0,
                        "min": 0.0,
                        "max": 1.0,
                        "step": 0.05,
                        "widget": "slider",
                        "applicable_tasks": ["text-generation", "conversational"]
                    },
                    "top_k": {
                        "type": "integer",
                        "label": "Top K",
                        "description": "Top K sampling (limits to K most likely tokens)",
                        "required": False,
                        "default": 50,
                        "min": 0,
                        "max": 100,
                        "widget": "number",
                        "applicable_tasks": ["text-generation"]
                    },
                    "num_return_sequences": {
                        "type": "integer",
                        "label": "Number of Sequences",
                        "description": "Number of output sequences to generate",
                        "required": False,
                        "default": 1,
                        "min": 1,
                        "max": 10,
                        "widget": "number",
                        "applicable_tasks": ["text-generation", "text-to-image"]
                    }
                }
            },
            
            # ============= TASK-SPECIFIC PARAMETERS =============
            # These will be dynamically shown based on the selected model's task
            "task_specific_parameters": {
                "type": "object",
                "label": "Task-Specific Parameters",
                "description": "Additional parameters specific to the model's task type",
                "widget": "hidden",  # Hide from UI - rendered dynamically based on task
                "required": False,
                "dynamic_based_on": "model_marketplace.task",
                "schemas": {
                    # ========== NLP TASKS ==========
                    "text-generation": {
                        "max_new_tokens": {
                            "type": "integer",
                            "label": "Max New Tokens",
                            "description": "Maximum number of tokens to generate",
                            "default": 50,
                            "min": 1,
                            "max": 2048
                        },
                        "do_sample": {
                            "type": "boolean",
                            "label": "Use Sampling",
                            "description": "Use sampling instead of greedy decoding",
                            "default": True
                        },
                        "return_full_text": {
                            "type": "boolean",
                            "label": "Return Full Text",
                            "description": "Return the full text (prompt + generation)",
                            "default": False
                        }
                    },
                    "text-classification": {
                        "return_all_scores": {
                            "type": "boolean",
                            "label": "Return All Scores",
                            "description": "Return scores for all labels (not just top 1)",
                            "default": False
                        }
                    },
                    "token-classification": {
                        "aggregation_strategy": {
                            "type": "select",
                            "label": "Aggregation Strategy",
                            "description": "How to aggregate sub-tokens",
                            "options": [
                                {"value": "none", "label": "None"},
                                {"value": "simple", "label": "Simple"},
                                {"value": "first", "label": "First"},
                                {"value": "average", "label": "Average"},
                                {"value": "max", "label": "Max"}
                            ],
                            "default": "simple"
                        }
                    },
                    "zero-shot-classification": {
                        "candidate_labels": {
                            "type": "string",
                            "label": "Candidate Labels",
                            "description": "Comma-separated list of possible labels (e.g., 'positive, negative, neutral')",
                            "widget": "textarea",
                            "required": True,
                            "placeholder": "label1, label2, label3"
                        },
                        "multi_label": {
                            "type": "boolean",
                            "label": "Multi-Label Classification",
                            "description": "Allow multiple labels to be true",
                            "default": False
                        }
                    },
                    "question-answering": {
                        "context": {
                            "type": "string",
                            "label": "Context",
                            "description": "Context text for question answering (can also be provided via input port)",
                            "widget": "textarea",
                            "required": False
                        },
                        "top_k": {
                            "type": "integer",
                            "label": "Top K Answers",
                            "description": "Return top K possible answers",
                            "default": 1,
                            "min": 1,
                            "max": 10
                        }
                    },
                    "table-question-answering": {
                        "query": {
                            "type": "string",
                            "label": "Query",
                            "description": "Question to ask about the table",
                            "required": False
                        }
                    },
                    "summarization": {
                        "min_length": {
                            "type": "integer",
                            "label": "Min Length",
                            "description": "Minimum length of summary",
                            "default": 10,
                            "min": 1
                        },
                        "max_length": {
                            "type": "integer",
                            "label": "Max Length",
                            "description": "Maximum length of summary",
                            "default": 100,
                            "min": 1,
                            "max": 1024
                        },
                        "do_sample": {
                            "type": "boolean",
                            "label": "Use Sampling",
                            "description": "Use sampling instead of greedy decoding",
                            "default": False
                        }
                    },
                    "translation": {
                        "src_lang": {
                            "type": "string",
                            "label": "Source Language",
                            "description": "Source language code (e.g., 'en', 'fr')",
                            "required": False,
                            "placeholder": "en"
                        },
                        "tgt_lang": {
                            "type": "string",
                            "label": "Target Language",
                            "description": "Target language code (e.g., 'es', 'de')",
                            "required": False,
                            "placeholder": "es"
                        }
                    },
                    "fill-mask": {
                        "top_k": {
                            "type": "integer",
                            "label": "Top K Predictions",
                            "description": "Return top K mask predictions",
                            "default": 5,
                            "min": 1,
                            "max": 20
                        }
                    },
                    "sentence-similarity": {
                        "source_sentence": {
                            "type": "string",
                            "label": "Source Sentence",
                            "description": "The sentence to compare against (if not provided via input)",
                            "widget": "textarea",
                            "required": False
                        },
                        "sentences": {
                            "type": "string",
                            "label": "Sentences to Compare",
                            "description": "Comma-separated or line-separated sentences to compare",
                            "widget": "textarea",
                            "required": False
                        }
                    },
                    "feature-extraction": {
                        "normalize": {
                            "type": "boolean",
                            "label": "Normalize Embeddings",
                            "description": "Normalize the output embeddings",
                            "default": False
                        }
                    },
                    "text-ranking": {
                        "query": {
                            "type": "string",
                            "label": "Query",
                            "description": "Query text for ranking",
                            "required": False
                        }
                    },
                    
                    # ========== COMPUTER VISION TASKS ==========
                    "image-classification": {
                        "top_k": {
                            "type": "integer",
                            "label": "Top K Results",
                            "description": "Return top K classification results",
                            "default": 5,
                            "min": 1,
                            "max": 20
                        }
                    },
                    "zero-shot-image-classification": {
                        "candidate_labels": {
                            "type": "string",
                            "label": "Candidate Labels",
                            "description": "Comma-separated list of possible labels",
                            "widget": "textarea",
                            "required": True,
                            "placeholder": "cat, dog, bird"
                        }
                    },
                    "object-detection": {
                        "threshold": {
                            "type": "number",
                            "label": "Confidence Threshold",
                            "description": "Minimum confidence score (0-1)",
                            "default": 0.5,
                            "min": 0.0,
                            "max": 1.0,
                            "step": 0.05
                        }
                    },
                    "zero-shot-object-detection": {
                        "candidate_labels": {
                            "type": "string",
                            "label": "Object Labels",
                            "description": "Comma-separated list of objects to detect",
                            "widget": "textarea",
                            "required": True,
                            "placeholder": "person, car, tree"
                        }
                    },
                    "image-segmentation": {
                        "threshold": {
                            "type": "number",
                            "label": "Threshold",
                            "description": "Segmentation threshold",
                            "default": 0.5,
                            "min": 0.0,
                            "max": 1.0,
                            "step": 0.05
                        }
                    },
                    "text-to-image": {
                        "negative_prompt": {
                            "type": "string",
                            "label": "Negative Prompt",
                            "description": "What to avoid in the image",
                            "widget": "textarea",
                            "required": False
                        },
                        "num_inference_steps": {
                            "type": "integer",
                            "label": "Inference Steps",
                            "description": "Number of denoising steps (more = better quality, slower)",
                            "default": 50,
                            "min": 1,
                            "max": 150
                        },
                        "guidance_scale": {
                            "type": "number",
                            "label": "Guidance Scale",
                            "description": "How closely to follow the prompt (higher = more adherence)",
                            "default": 7.5,
                            "min": 1.0,
                            "max": 20.0,
                            "step": 0.5
                        },
                        "width": {
                            "type": "integer",
                            "label": "Width",
                            "description": "Image width in pixels",
                            "default": 512,
                            "min": 64,
                            "max": 2048
                        },
                        "height": {
                            "type": "integer",
                            "label": "Height",
                            "description": "Image height in pixels",
                            "default": 512,
                            "min": 64,
                            "max": 2048
                        }
                    },
                    "image-to-text": {
                        "max_new_tokens": {
                            "type": "integer",
                            "label": "Max Tokens",
                            "description": "Maximum tokens in caption",
                            "default": 50,
                            "min": 1,
                            "max": 200
                        }
                    },
                    "image-to-image": {
                        "strength": {
                            "type": "number",
                            "label": "Transformation Strength",
                            "description": "How much to transform the input image (0-1)",
                            "default": 0.8,
                            "min": 0.0,
                            "max": 1.0,
                            "step": 0.05
                        },
                        "guidance_scale": {
                            "type": "number",
                            "label": "Guidance Scale",
                            "description": "How closely to follow the prompt",
                            "default": 7.5,
                            "min": 1.0,
                            "max": 20.0,
                            "step": 0.5
                        }
                    },
                    "depth-estimation": {
                        "return_map": {
                            "type": "boolean",
                            "label": "Return Depth Map",
                            "description": "Return the depth map as an image",
                            "default": True
                        }
                    },
                    "mask-generation": {
                        "points_per_batch": {
                            "type": "integer",
                            "label": "Points Per Batch",
                            "description": "Number of points to sample per batch",
                            "default": 64,
                            "min": 1,
                            "max": 256
                        }
                    },
                    
                    # ========== AUDIO TASKS ==========
                    "automatic-speech-recognition": {
                        "return_timestamps": {
                            "type": "boolean",
                            "label": "Return Timestamps",
                            "description": "Include word-level timestamps",
                            "default": False
                        },
                        "language": {
                            "type": "string",
                            "label": "Language",
                            "description": "Language code (e.g., 'en', 'es'). Leave empty for auto-detect",
                            "required": False,
                            "placeholder": "en"
                        }
                    },
                    "audio-classification": {
                        "top_k": {
                            "type": "integer",
                            "label": "Top K Results",
                            "description": "Return top K classification results",
                            "default": 5,
                            "min": 1,
                            "max": 10
                        }
                    },
                    "text-to-speech": {
                        "speaker_id": {
                            "type": "integer",
                            "label": "Speaker ID",
                            "description": "Voice/speaker ID (if model supports multiple voices)",
                            "required": False,
                            "min": 0
                        }
                    },
                    "text-to-audio": {
                        "duration": {
                            "type": "number",
                            "label": "Duration (seconds)",
                            "description": "Target audio duration",
                            "default": 5.0,
                            "min": 0.1,
                            "max": 30.0
                        }
                    },
                    "audio-to-audio": {
                        "target_sr": {
                            "type": "integer",
                            "label": "Target Sample Rate",
                            "description": "Target audio sample rate (Hz)",
                            "default": 16000,
                            "min": 8000,
                            "max": 48000
                        }
                    },
                    
                    # ========== MULTIMODAL TASKS ==========
                    "visual-question-answering": {
                        "top_k": {
                            "type": "integer",
                            "label": "Top K Answers",
                            "description": "Return top K possible answers",
                            "default": 1,
                            "min": 1,
                            "max": 5
                        }
                    },
                    "document-question-answering": {
                        "top_k": {
                            "type": "integer",
                            "label": "Top K Answers",
                            "description": "Return top K possible answers",
                            "default": 1,
                            "min": 1,
                            "max": 5
                        }
                    },
                    "image-text-to-text": {
                        "max_new_tokens": {
                            "type": "integer",
                            "label": "Max New Tokens",
                            "description": "Maximum tokens to generate",
                            "default": 100,
                            "min": 1,
                            "max": 500
                        }
                    },
                    
                    # ========== DEFAULT FOR UNSPECIFIED TASKS ==========
                    "conversational": {
                        "max_length": {
                            "type": "integer",
                            "label": "Max Length",
                            "description": "Maximum response length",
                            "default": 100,
                            "min": 1,
                            "max": 500
                        }
                    }
                }
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Execute HuggingFace inference"""
        try:
            import time
            start_time = time.time()
            
            # Get configuration
            huggingface_marketplace = self.config.get("huggingface_marketplace", {})
            model_id = huggingface_marketplace.get("model_id")
            task = huggingface_marketplace.get("task")
            
            inference_mode = self.config.get("inference_mode", "local")
            credential_id = self.config.get("credential_id")
            
            # Validate model selection
            if not model_id:
                raise ValueError("No model selected. Please select a model from the marketplace.")
            
            # Get input data
            input_value = input_data.ports.get("input")
            if input_value is None:
                raise ValueError("Input is required")
            
            # Get parameters (merge config params with port params)
            common_params = self.config.get("common_parameters") or {}
            task_params = self.config.get("task_specific_parameters") or {}
            port_params = input_data.ports.get("parameters") or {}
            
            # Ensure all are dictionaries
            if not isinstance(common_params, dict):
                common_params = {}
            if not isinstance(task_params, dict):
                task_params = {}
            if not isinstance(port_params, dict):
                port_params = {}
            
            # Merge parameters (port params override config params)
            merged_params = {**common_params, **task_params, **port_params}
            
            # Remove None values and filter by applicable tasks
            final_params = {k: v for k, v in merged_params.items() if v is not None}
            
            logger.info(
                f"🤗 HuggingFace Inference executing:\n"
                f"  Model: {model_id}\n"
                f"  Task: {task}\n"
                f"  Mode: {inference_mode}\n"
                f"  Parameters: {final_params}"
            )
            
            # Get HuggingFace manager
            from app.core.ai.huggingface_manager import (
                get_huggingface_manager,
                InferenceMode,
                HFTaskType
            )
            
            # Get API token if in API mode
            hf_token = None
            if inference_mode == "api":
                if not credential_id:
                    raise ValueError("HuggingFace API credential required for API mode. Please select a credential or use Local mode.")
                
                # Get credential from credential manager
                from app.services.credential_manager import CredentialManager
                from app.database.session import SessionLocal
                
                db = SessionLocal()
                try:
                    cred_manager = CredentialManager(db)
                    credential = cred_manager.get_credential_data(
                        credential_id=credential_id,
                        user_id=input_data.config.get("_user_id")  # Injected by executor
                    )
                    
                    # credential can be either a dict or an object with credential_data attribute
                    if isinstance(credential, dict):
                        hf_token = credential.get("api_key")
                    else:
                        hf_token = credential.credential_data.get("api_key")
                    
                    if not hf_token:
                        raise ValueError("Invalid HuggingFace credential: missing api_key")
                    
                    logger.info(f"✅ Retrieved HuggingFace API token from credential {credential_id}")
                finally:
                    db.close()
            
            # Initialize manager
            hf_manager = get_huggingface_manager(hf_token=hf_token)
            
            # Get advanced options
            advanced = self.config.get("advanced_options", {})
            
            # Run inference
            mode_enum = InferenceMode.LOCAL if inference_mode == "local" else InferenceMode.API
            
            # Convert task string to enum if available
            task_enum = None
            if task:
                try:
                    task_enum = HFTaskType(task)
                except ValueError:
                    logger.warning(f"Unknown task type: {task}, will let HuggingFace auto-detect")
            
            # Prepare inference arguments
            infer_args = {
                "model_id": model_id,
                "inputs": input_value,
                "mode": mode_enum,
                "task": task_enum,
                "parameters": final_params if final_params else None,
            }
            
            # Add mode-specific arguments
            if inference_mode == "api":
                infer_args["options"] = {
                    "use_cache": advanced.get("use_cache", True),
                    "wait_for_model": advanced.get("wait_for_model", True)
                }
            else:
                infer_args["pipeline_kwargs"] = {}
            
            result = await hf_manager.infer(**infer_args)
            
            execution_time = time.time() - start_time
            
            # Build metadata
            metadata = {
                "model_id": model_id,
                "task": task,
                "inference_mode": inference_mode,
                "execution_time_seconds": round(execution_time, 2),
                "parameters_used": final_params,
                "is_cached": hf_manager.is_model_cached(model_id) if inference_mode == "local" else False
            }
            
            logger.info(
                f"✅ HuggingFace Inference completed: {model_id} "
                f"({execution_time:.2f}s, mode={inference_mode})"
            )
            
            return {
                "output": result,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ HuggingFace Inference error: {e}", exc_info=True)
            return {
                "output": None,
                "metadata": {"error": str(e)},
                "error": str(e)
            }


