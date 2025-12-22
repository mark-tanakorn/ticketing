"""
Custom Nodes - chat + conversation endpoints.

Split out from endpoints/custom_nodes.py to keep modules small.
"""

import json
import logging
import re
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_smart, get_db
from app.api.v1.schemas.custom_nodes import (
    ConversationDetail,
    ConversationDetailResponse,
    ConversationListResponse,
    GenerateCodeResponse,
    MessageResponse,
    NodeValidationRequest,
    NodeValidationResponse,
    RefineCodeRequest,
    SaveNodeRequest,
    SaveNodeResponse,
    SendMessageRequest,
    StartConversationRequest,
    StartConversationResponse,
    StartConversationStreamRequest,
    UpdateConversationCodeRequest,
    UpdateConversationCodeResponse,
    ValidationError,
)
from app.database.models.conversation import Conversation, ConversationMessage, CustomNode
from app.database.models.user import User
from app.utils.custom_node_metadata import extract_custom_node_metadata

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_ATTACHMENTS_PER_MESSAGE = 5


@router.post("/conversations/start", response_model=StartConversationResponse)
async def start_conversation(
    request: StartConversationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart),
):
    logger.info(f"🆕 Starting conversation: user={current_user.id}, provider={request.provider}, model={request.model}")
    try:
        conversation_id = str(uuid.uuid4())
        title = "New Custom Node"

        conversation = Conversation(
            id=conversation_id,
            user_id=current_user.id,
            title=title,
            status="active",
            provider=request.provider,
            model=request.model,
            temperature=str(request.temperature) if request.temperature else "0.3",
            requirements=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(conversation)

        from app.services.conversation_manager import ConversationManager

        manager = ConversationManager(db)
        assistant_message = ""

        if request.initial_message:
            user_msg = ConversationMessage(
                conversation_id=conversation_id,
                role="user",
                content=request.initial_message,
                created_at=datetime.utcnow(),
                activity={"attachments": [a.model_dump() for a in (request.attachments or [])][:MAX_ATTACHMENTS_PER_MESSAGE]} if request.attachments else None,
            )
            db.add(user_msg)

            response = await manager.process_message(
                conversation=conversation,
                user_message=request.initial_message,
                attachments=[a.model_dump() for a in (request.attachments or [])][:MAX_ATTACHMENTS_PER_MESSAGE] if request.attachments else None,
                user_id=current_user.id,
            )
            conversation.title = manager.generate_title(request.initial_message)
            assistant_message = response["assistant_message"]

            msg = ConversationMessage(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_message,
                provider=request.provider,
                model=request.model,
                created_at=datetime.utcnow(),
            )
            db.add(msg)
        else:
            assistant_message = await manager.get_initial_message()
            msg = ConversationMessage(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_message,
                provider=request.provider,
                model=request.model,
                created_at=datetime.utcnow(),
            )
            db.add(msg)

        db.commit()
        return StartConversationResponse(
            success=True,
            conversation_id=conversation_id,
            title=conversation.title,
            assistant_message=assistant_message,
            provider=request.provider,
            model=request.model,
        )
    except Exception as e:
        logger.error(f"❌ Failed to start conversation: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to start conversation: {str(e)}")


@router.post("/conversations/start/stream")
async def start_conversation_stream(
    request: StartConversationStreamRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart),
):
    """
    Start a new conversation and stream the first assistant response.
    This makes the first message behave the same as normal /messages/stream calls,
    including Activity and tool_start/tool_end events.
    """
    logger.info(f"🆕💬 Streaming start conversation: user={current_user.id}, provider={request.provider}, model={request.model}")

    async def generate_stream():
        try:
            from app.services.conversation_manager import ConversationManager

            manager = ConversationManager(db)
            conversation_id = str(uuid.uuid4())
            title = manager.generate_title(request.message)

            conversation = Conversation(
                id=conversation_id,
                user_id=current_user.id,
                title=title,
                status="active",
                provider=request.provider,
                model=request.model,
                temperature=str(request.temperature) if request.temperature else "0.3",
                requirements=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(conversation)

            user_msg = ConversationMessage(
                conversation_id=conversation_id,
                role="user",
                content=request.message,
                created_at=datetime.utcnow(),
                activity={"attachments": [a.model_dump() for a in (request.attachments or [])][:MAX_ATTACHMENTS_PER_MESSAGE]} if request.attachments else None,
            )
            db.add(user_msg)
            db.commit()

            # Tell the client the conversation exists (so it can switch off the welcome state)
            yield f"data: {json.dumps({'type': 'conversation_started', 'conversation_id': conversation_id, 'title': title, 'provider': request.provider, 'model': request.model, 'temperature': request.temperature})}\n\n"

            manager_stream = manager.process_message_stream(
                conversation=conversation,
                user_message=request.message,
                attachments=[a.model_dump() for a in (request.attachments or [])][:MAX_ATTACHMENTS_PER_MESSAGE] if request.attachments else None,
                user_id=current_user.id,
            )

            full_message = ""
            ready_to_generate = False
            requirements = None
            generated_code = None
            workflow_draft: Optional[Dict[str, Any]] = None
            activity_events = []

            async for chunk in manager_stream:
                if chunk["type"] == "token":
                    full_message += chunk["content"]
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk['content']})}\n\n"
                elif chunk["type"] == "status":
                    activity_events.append({"kind": "status", "message": chunk.get("message", ""), "at": datetime.utcnow().isoformat()})
                    yield f"data: {json.dumps({'type': 'status', 'message': chunk.get('message', '')})}\n\n"
                elif chunk["type"] == "workflow_draft":
                    workflow_draft = chunk.get("workflow")
                    activity_events.append(
                        {
                            "kind": "event",
                            "event": {"type": "workflow_draft", "workflow": workflow_draft},
                            "at": datetime.utcnow().isoformat(),
                        }
                    )
                    yield f"data: {json.dumps({'type': 'workflow_draft', 'workflow': workflow_draft})}\n\n"
                elif chunk["type"] == "done":
                    full_message = chunk["assistant_message"]
                    ready_to_generate = chunk["ready_to_generate"]
                    requirements = chunk.get("requirements")
                    generated_code = chunk.get("generated_code")
                    workflow_draft = chunk.get("workflow_draft") or workflow_draft
                else:
                    if chunk.get("type") == "tool_start":
                        activity_events.append({"kind": "tool_start", "tool": chunk.get("tool"), "at": datetime.utcnow().isoformat()})
                    elif chunk.get("type") == "tool_end":
                        activity_events.append({"kind": "tool_end", "tool": chunk.get("tool"), "at": datetime.utcnow().isoformat()})
                    else:
                        activity_events.append({"kind": "event", "event": chunk, "at": datetime.utcnow().isoformat()})
                    yield f"data: {json.dumps(chunk)}\n\n"

            # Persist assistant message (+ activity, including workflow payload)
            assistant_msg = ConversationMessage(
                conversation_id=conversation_id,
                role="assistant",
                content=full_message,
                provider=request.provider,
                model=request.model,
                activity=activity_events or None,
                created_at=datetime.utcnow(),
            )
            db.add(assistant_msg)

            conversation.updated_at = datetime.utcnow()
            if requirements:
                conversation.requirements = requirements

            # If code was generated, validate and attach to conversation (same as normal stream endpoint)
            if generated_code:
                try:
                    from app.services.code_validator import NodeCodeValidator

                    logger.info("✨ Code found in response, validating...")
                    activity_events.append({"kind": "status", "message": "Validating generated code...", "at": datetime.utcnow().isoformat()})
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Validating generated code...'})}\n\n"

                    validator = NodeCodeValidator()
                    validation = validator.validate(generated_code)

                    node_type_match = re.search(r"@register_node\(\s*['\"]([^'\"]+)['\"]", generated_code)
                    node_type = node_type_match.group(1) if node_type_match else "custom_node"

                    class_name_match = re.search(r"class\s+(\w+)\s*\(", generated_code)
                    class_name = class_name_match.group(1) if class_name_match else "CustomNode"

                    conversation.generated_code = generated_code
                    conversation.node_type = node_type
                    conversation.class_name = class_name
                    conversation.validation_status = "valid" if validation["valid"] else "invalid"
                    conversation.validation_errors = validation.get("errors")
                    conversation.status = "refining" if validation["valid"] else "failed"

                    db.commit()
                    activity_events.append({"kind": "event", "event": {"type": "generation_complete", "success": True, "node_type": node_type}, "at": datetime.utcnow().isoformat()})
                    yield f"data: {json.dumps({'type': 'generation_complete', 'success': True, 'node_type': node_type})}\n\n"
                except Exception as e:
                    logger.error(f"❌ Failed to process generated code: {e}", exc_info=True)
                    activity_events.append({"kind": "event", "event": {"type": "generation_complete", "success": False, "error": str(e)}, "at": datetime.utcnow().isoformat()})
                    yield f"data: {json.dumps({'type': 'generation_complete', 'success': False, 'error': str(e)})}\n\n"

            db.commit()
            yield f"data: {json.dumps({'type': 'done', 'ready_to_generate': ready_to_generate, 'requirements': requirements})}\n\n"
        except Exception as e:
            logger.error(f"❌ Start stream failed: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.post("/conversations/{conversation_id}/messages/stream")
async def send_message_stream(
    conversation_id: str,
    request: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart),
):
    logger.info(f"💬 Streaming message in conversation {conversation_id}")

    async def generate_stream():
        try:
            conversation = (
                db.query(Conversation)
                .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
                .first()
            )
            if not conversation:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Conversation not found'})}\n\n"
                return

            if conversation.status not in ["active", "refining", "failed", "generating", "completed"]:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Conversation is {conversation.status}'})}\n\n"
                return

            if conversation.status in ["failed", "generating", "completed"]:
                conversation.status = "active"
                db.commit()

            # Allow per-message overrides of provider/model/temperature (applies to subsequent turns too)
            if request.provider:
                conversation.provider = request.provider
            if request.model:
                conversation.model = request.model
            if request.temperature is not None:
                conversation.temperature = str(request.temperature)
            if request.provider or request.model or request.temperature is not None:
                db.commit()

            user_msg = ConversationMessage(
                conversation_id=conversation_id,
                role="user",
                content=request.message,
                created_at=datetime.utcnow(),
                activity={"attachments": [a.model_dump() for a in (request.attachments or [])][:MAX_ATTACHMENTS_PER_MESSAGE]} if request.attachments else None,
            )
            db.add(user_msg)
            db.commit()

            from app.services.conversation_manager import ConversationManager

            manager = ConversationManager(db)
            manager_stream = manager.process_message_stream(
                conversation=conversation,
                user_message=request.message,
                attachments=[a.model_dump() for a in (request.attachments or [])][:MAX_ATTACHMENTS_PER_MESSAGE] if request.attachments else None,
                user_id=current_user.id,
            )

            full_message = ""
            ready_to_generate = False
            requirements = None
            generated_code = None
            workflow_draft: Optional[Dict[str, Any]] = None
            workflow_draft_activity_recorded = False
            activity_events = []

            async for chunk in manager_stream:
                if chunk["type"] == "token":
                    full_message += chunk["content"]
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk['content']})}\n\n"
                elif chunk["type"] == "status":
                    activity_events.append({"kind": "status", "message": chunk.get("message", ""), "at": datetime.utcnow().isoformat()})
                    yield f"data: {json.dumps({'type': 'status', 'message': chunk.get('message', '')})}\n\n"
                elif chunk["type"] == "workflow_draft":
                    workflow_draft = chunk.get("workflow")
                    # Persist the actual workflow JSON on the assistant message so re-opening the conversation
                    # can rehydrate the workflow preview UI.
                    activity_events.append(
                        {
                            "kind": "event",
                            "event": {"type": "workflow_draft", "workflow": workflow_draft},
                            "at": datetime.utcnow().isoformat(),
                        }
                    )
                    workflow_draft_activity_recorded = True
                    yield f"data: {json.dumps({'type': 'workflow_draft', 'workflow': workflow_draft})}\n\n"
                elif chunk["type"] == "done":
                    full_message = chunk["assistant_message"]
                    ready_to_generate = chunk["ready_to_generate"]
                    requirements = chunk.get("requirements")
                    generated_code = chunk.get("generated_code")
                    workflow_draft = chunk.get("workflow_draft") or workflow_draft
                else:
                    if chunk.get("type") == "tool_start":
                        activity_events.append({"kind": "tool_start", "tool": chunk.get("tool"), "at": datetime.utcnow().isoformat()})
                    elif chunk.get("type") == "tool_end":
                        activity_events.append({"kind": "tool_end", "tool": chunk.get("tool"), "at": datetime.utcnow().isoformat()})
                    else:
                        activity_events.append({"kind": "event", "event": chunk, "at": datetime.utcnow().isoformat()})
                    yield f"data: {json.dumps(chunk)}\n\n"

            # Some model paths may only provide the workflow draft on the final "done" chunk.
            # Ensure we persist it on the assistant message for reloads.
            if workflow_draft and not workflow_draft_activity_recorded:
                activity_events.append(
                    {
                        "kind": "event",
                        "event": {"type": "workflow_draft", "workflow": workflow_draft},
                        "at": datetime.utcnow().isoformat(),
                    }
                )

            # If the model proposed missing custom nodes, auto-create DB-only drafts (no .py saved yet).
            # User will review/edit + register from My Nodes.
            if workflow_draft and isinstance(workflow_draft, dict) and workflow_draft.get("missing_custom_nodes"):
                missing = workflow_draft.get("missing_custom_nodes") or []
                if isinstance(missing, list) and missing:
                    # Hard cap to avoid runaway costs
                    missing = missing[:3]
                    yield f"data: {json.dumps({'type': 'status', 'message': f'Creating {len(missing)} custom node draft(s)…'})}\n\n"
                    activity_events.append({"kind": "status", "message": f"Creating {len(missing)} custom node draft(s)…", "at": datetime.utcnow().isoformat()})

                    from app.core.ai.manager import LangChainManager
                    from app.services.code_validator import NodeCodeValidator

                    llm = LangChainManager(db)
                    validator = NodeCodeValidator()

                    def unique_node_type(base: str) -> str:
                        base_clean = re.sub(r'[^a-zA-Z0-9_]', '_', (base or "custom_node").strip().lower())
                        if not base_clean:
                            base_clean = "custom_node"
                        candidate = base_clean
                        i = 2
                        while db.query(CustomNode).filter(CustomNode.node_type == candidate).first():
                            candidate = f"{base_clean}_{i}"
                            i += 1
                        return candidate

                    for spec in missing:
                        try:
                            spec = spec or {}
                            requested_type = spec.get("node_type") or spec.get("name") or "custom_node"
                            node_type = unique_node_type(str(requested_type))

                            prompt = (
                                "You are an expert Python developer specializing in creating workflow nodes.\n\n"
                                "Generate ONLY Python code (no markdown, no explanations) for a Node class using @register_node.\n"
                                "Follow these security rules:\n"
                                "- Do NOT use os, subprocess, eval, exec, __import__, sys, socket\n"
                                "- Do NOT use open() or write/delete operations\n"
                                "- Allowed imports include: app.core.nodes.base, app.core.nodes.registry, app.schemas.workflow, typing, logging, json, datetime, httpx\n\n"
                                "Node spec (JSON):\n"
                                f"{json.dumps({**spec, 'node_type': node_type}, ensure_ascii=False)}\n"
                            )

                            code = await llm.call_llm(
                                prompt=prompt,
                                provider=conversation.provider,
                                model=conversation.model,
                                temperature=0.2,
                                fallback=True,
                            )
                            # Basic cleanup (sometimes models add fences)
                            code = re.sub(r"^```(?:python)?\s*", "", code.strip(), flags=re.IGNORECASE)
                            code = re.sub(r"\s*```$", "", code.strip())

                            validation = validator.validate(code)
                            meta = extract_custom_node_metadata(code or "")

                            draft = CustomNode(
                                user_id=current_user.id,
                                conversation_id=conversation.id,
                                node_type=node_type,
                                display_name=meta.name or spec.get("name") or node_type,
                                description=meta.description or spec.get("description") or None,
                                category=meta.category or spec.get("category") or "processing",
                                icon=meta.icon or spec.get("icon") or None,
                                code=code,
                                file_path=None,
                                is_active=True,
                                is_registered=False,
                                version=meta.version or spec.get("version") or "1.0.0",
                                input_ports=spec.get("inputs"),
                                output_ports=spec.get("outputs"),
                                config_schema=spec.get("config"),
                                created_at=datetime.utcnow(),
                                updated_at=datetime.utcnow(),
                            )
                            db.add(draft)
                            db.commit()
                            db.refresh(draft)

                            yield f"data: {json.dumps({'type': 'custom_node_draft_created', 'custom_node_id': draft.id, 'node_type': draft.node_type, 'display_name': draft.display_name, 'valid': bool(validation.get('valid'))})}\n\n"
                            activity_events.append({"kind": "event", "event": {"type": "custom_node_draft_created", "custom_node_id": draft.id, "node_type": draft.node_type}, "at": datetime.utcnow().isoformat()})
                        except Exception as draft_err:
                            logger.error(f"❌ Failed creating custom node draft: {draft_err}", exc_info=True)
                            yield f"data: {json.dumps({'type': 'custom_node_draft_failed', 'error': str(draft_err)})}\n\n"
                            activity_events.append({"kind": "event", "event": {"type": "custom_node_draft_failed", "error": str(draft_err)}, "at": datetime.utcnow().isoformat()})

            assistant_msg = ConversationMessage(
                conversation_id=conversation_id,
                role="assistant",
                content=full_message,
                provider=conversation.provider,
                model=conversation.model,
                activity=activity_events or None,
                created_at=datetime.utcnow(),
            )
            db.add(assistant_msg)

            conversation.updated_at = datetime.utcnow()
            if requirements:
                conversation.requirements = requirements

            if generated_code:
                try:
                    from app.services.code_validator import NodeCodeValidator

                    logger.info("✨ Code found in response, validating...")
                    activity_events.append({"kind": "status", "message": "Validating generated code...", "at": datetime.utcnow().isoformat()})
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Validating generated code...'})}\n\n"

                    validator = NodeCodeValidator()
                    validation = validator.validate(generated_code)

                    # NOTE: raw regex string; do not double-escape parentheses.
                    node_type_match = re.search(r"@register_node\(\s*['\"]([^'\"]+)['\"]", generated_code)
                    node_type = node_type_match.group(1) if node_type_match else "custom_node"

                    class_name_match = re.search(r"class\s+(\w+)\s*\(", generated_code)
                    class_name = class_name_match.group(1) if class_name_match else "CustomNode"

                    conversation.generated_code = generated_code
                    conversation.node_type = node_type
                    conversation.class_name = class_name
                    conversation.validation_status = "valid" if validation["valid"] else "invalid"
                    conversation.validation_errors = validation.get("errors")
                    conversation.status = "refining" if validation["valid"] else "failed"

                    db.commit()
                    activity_events.append({"kind": "event", "event": {"type": "generation_complete", "success": True, "node_type": node_type}, "at": datetime.utcnow().isoformat()})
                    yield f"data: {json.dumps({'type': 'generation_complete', 'success': True, 'node_type': node_type})}\n\n"
                except Exception as e:
                    logger.error(f"❌ Failed to process generated code: {e}", exc_info=True)
                    activity_events.append({"kind": "event", "event": {"type": "generation_complete", "success": False, "error": str(e)}, "at": datetime.utcnow().isoformat()})
                    yield f"data: {json.dumps({'type': 'generation_complete', 'success': False, 'error': str(e)})}\n\n"

            db.commit()
            yield f"data: {json.dumps({'type': 'done', 'ready_to_generate': ready_to_generate, 'requirements': requirements})}\n\n"
        except Exception as e:
            logger.error(f"❌ Stream failed: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart),
):
    logger.info(f"📋 Listing conversations for user {current_user.id}")
    try:
        query = db.query(Conversation).filter(Conversation.user_id == current_user.id)
        if status:
            query = query.filter(Conversation.status == status)
        conversations = query.order_by(Conversation.updated_at.desc()).limit(limit).all()

        conversation_list = [
            ConversationDetail(
                id=conv.id,
                title=conv.title,
                status=conv.status,
                provider=conv.provider,
                model=conv.model,
                temperature=conv.temperature,
                requirements=conv.requirements,
                generated_code=conv.generated_code,
                node_type=conv.node_type,
                class_name=conv.class_name,
                validation_status=conv.validation_status,
                validation_errors=conv.validation_errors,
                message_count=conv.message_count,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                completed_at=conv.completed_at,
            )
            for conv in conversations
        ]
        return ConversationListResponse(success=True, conversations=conversation_list, total=len(conversation_list))
    except Exception as e:
        logger.error(f"❌ Failed to list conversations: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list conversations: {str(e)}")


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart),
):
    logger.info(f"📖 Getting conversation {conversation_id}")
    try:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
            .first()
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        messages = [
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
                provider=msg.provider,
                model=msg.model,
                activity=getattr(msg, "activity", None),
            )
            for msg in conversation.messages
        ]

        conversation_detail = ConversationDetail(
            id=conversation.id,
            title=conversation.title,
            status=conversation.status,
            provider=conversation.provider,
            model=conversation.model,
            temperature=conversation.temperature,
            requirements=conversation.requirements,
            generated_code=conversation.generated_code,
            node_type=conversation.node_type,
            class_name=conversation.class_name,
            validation_status=conversation.validation_status,
            validation_errors=conversation.validation_errors,
            message_count=conversation.message_count,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            completed_at=conversation.completed_at,
        )

        return ConversationDetailResponse(success=True, conversation=conversation_detail, messages=messages)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get conversation: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get conversation: {str(e)}")


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart),
):
    logger.info(f"🗑️ Deleting conversation {conversation_id}")
    try:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
            .first()
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        db.delete(conversation)
        db.commit()
        return {"success": True, "message": "Conversation deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete conversation: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete conversation: {str(e)}")


@router.post("/conversations/{conversation_id}/generate", response_model=GenerateCodeResponse)
async def generate_code(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart),
):
    logger.info(f"✨ Generating code for conversation {conversation_id}")
    try:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
            .first()
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        conversation.status = "generating"
        db.commit()

        from app.services.node_generator import NodeGenerator
        from app.services.code_validator import NodeCodeValidator

        generator = NodeGenerator(db)
        result = await generator.generate_from_conversation(conversation)

        validator = NodeCodeValidator()
        validation = validator.validate(result["code"])

        conversation.generated_code = result["code"]
        conversation.node_type = result.get("node_type")
        conversation.class_name = result.get("class_name")
        conversation.validation_status = "valid" if validation["valid"] else "invalid"
        conversation.validation_errors = validation.get("errors")
        conversation.status = "refining" if validation["valid"] else "failed"
        conversation.updated_at = datetime.utcnow()
        db.commit()

        return GenerateCodeResponse(
            success=True,
            code=result["code"],
            node_type=result["node_type"],
            class_name=result["class_name"],
            validation_status="valid" if validation["valid"] else "invalid",
            validation_errors=validation.get("errors"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Code generation failed: {e}", exc_info=True)
        db.rollback()
        try:
            c = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if c:
                c.status = "failed"
                db.commit()
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate code: {str(e)}")


@router.post("/conversations/{conversation_id}/refine", response_model=GenerateCodeResponse)
async def refine_code(
    conversation_id: str,
    request: RefineCodeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart),
):
    logger.info(f"🔄 Refining code for conversation {conversation_id}")
    try:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
            .first()
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if not conversation.generated_code:
            raise HTTPException(status_code=400, detail="No code generated yet")

        user_msg = ConversationMessage(
            conversation_id=conversation_id,
            role="user",
            content=f"[Refinement Request] {request.refinement_request}",
            created_at=datetime.utcnow(),
        )
        db.add(user_msg)

        from app.services.node_generator import NodeGenerator
        from app.services.code_validator import NodeCodeValidator

        generator = NodeGenerator(db)
        result = await generator.refine_code(conversation=conversation, refinement_request=request.refinement_request)

        validator = NodeCodeValidator()
        validation = validator.validate(result["code"])

        conversation.generated_code = result["code"]
        conversation.validation_status = "valid" if validation["valid"] else "invalid"
        conversation.validation_errors = validation.get("errors")
        conversation.updated_at = datetime.utcnow()

        assistant_msg = ConversationMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=f"[Refinement] {result.get('explanation', 'Code updated')}",
            provider=conversation.provider,
            model=conversation.model,
            created_at=datetime.utcnow(),
        )
        db.add(assistant_msg)
        db.commit()

        return GenerateCodeResponse(
            success=True,
            code=result["code"],
            node_type=conversation.node_type or "",
            class_name=conversation.class_name or "",
            validation_status="valid" if validation["valid"] else "invalid",
            validation_errors=validation.get("errors"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Code refinement failed: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to refine code: {str(e)}")


@router.post("/validate", response_model=NodeValidationResponse)
async def validate_node_code(
    request: NodeValidationRequest,
    current_user: User = Depends(get_current_user_smart),
):
    logger.info("🔍 Validating node code")
    _ = current_user
    try:
        from app.services.code_validator import NodeCodeValidator

        validator = NodeCodeValidator()
        result = validator.validate(request.code)
        errors = [ValidationError(message=err, severity="error") for err in result.get("errors", [])]
        warnings = [ValidationError(message=warn, severity="warning") for warn in result.get("warnings", [])]
        return NodeValidationResponse(
            valid=result["valid"],
            errors=errors,
            warnings=warnings,
            node_type=result.get("node_type"),
            class_name=result.get("class_name"),
            message="Validation complete" if result["valid"] else "Validation failed",
        )
    except Exception as e:
        logger.error(f"❌ Validation error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to validate node code: {str(e)}")


@router.post("/save", response_model=SaveNodeResponse)
async def save_custom_node(
    request: SaveNodeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart),
):
    logger.info(f"💾 Saving custom node from conversation {request.conversation_id}")
    try:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == request.conversation_id, Conversation.user_id == current_user.id)
            .first()
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        code = request.code or conversation.generated_code
        if not code:
            raise HTTPException(status_code=400, detail="No code to save")

        from app.services.code_validator import NodeCodeValidator
        from app.services.node_saver import NodeSaver

        validator = NodeCodeValidator()
        validation = validator.validate(code)
        if not validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Code validation failed: {validation['errors']}",
            )

        node_type = validation.get("node_type")
        if not node_type:
            raise HTTPException(status_code=400, detail="Validation did not produce node_type")

        existing_node = db.query(CustomNode).filter(CustomNode.node_type == node_type).first()
        if existing_node:
            if not request.overwrite:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Node type '{node_type}' already exists. Set overwrite=True to replace it.")
            if existing_node.user_id != current_user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Node type '{node_type}' already exists and belongs to another user.")

        saver = NodeSaver()
        save_result = saver.save_node(code=code, node_type=node_type, overwrite=request.overwrite)

        # Sync display metadata from source code (source-of-truth)
        meta = extract_custom_node_metadata(code or "")

        if existing_node:
            existing_node.conversation_id = conversation.id
            existing_node.display_name = meta.name or conversation.title
            existing_node.description = meta.description or (conversation.requirements.get("functionality") if conversation.requirements else None)
            existing_node.category = meta.category or (conversation.requirements.get("category", "processing") if conversation.requirements else "processing")
            existing_node.icon = meta.icon or (conversation.requirements.get("icon") if conversation.requirements else None)
            if meta.version:
                existing_node.version = meta.version
            existing_node.code = code
            existing_node.file_path = save_result["file_path"]
            existing_node.is_active = True
            existing_node.is_registered = False
            existing_node.updated_at = datetime.utcnow()
            custom_node = existing_node
        else:
            custom_node = CustomNode(
                user_id=current_user.id,
                conversation_id=conversation.id,
                node_type=node_type,
                display_name=meta.name or conversation.title,
                description=meta.description or (conversation.requirements.get("functionality") if conversation.requirements else None),
                category=meta.category or (conversation.requirements.get("category", "processing") if conversation.requirements else "processing"),
                icon=meta.icon or (conversation.requirements.get("icon") if conversation.requirements else None),
                code=code,
                file_path=save_result["file_path"],
                is_active=True,
                is_registered=False,
                version=meta.version or "1.0.0",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(custom_node)

        conversation.status = "refining"
        conversation.custom_node_id = custom_node.id
        db.commit()

        try:
            from app.services.node_reloader import NodeReloader

            reloader = NodeReloader()
            await reloader.reload_custom_nodes()
            custom_node.is_registered = True
            db.commit()
            registered = True
        except Exception as reload_error:
            logger.warning(f"⚠️ Hot-reload failed: {reload_error}")
            registered = False

        return SaveNodeResponse(
            success=True,
            node_type=node_type,
            file_path=save_result["file_path"],
            message=save_result["message"],
            registered=registered,
        )
    except HTTPException:
        raise
    except FileExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Failed to save node: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save node: {str(e)}")


@router.post("/conversations/{conversation_id}/code", response_model=UpdateConversationCodeResponse)
async def update_conversation_code(
    conversation_id: str,
    request: UpdateConversationCodeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart),
):
    logger.info(f"📝 Updating conversation code: {conversation_id}")
    try:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
            .first()
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        code = (request.code or "").strip()
        if not code:
            raise HTTPException(status_code=400, detail="Code cannot be empty")

        from app.services.code_validator import NodeCodeValidator

        validator = NodeCodeValidator()
        validation = validator.validate(code)

        conversation.generated_code = code
        conversation.node_type = validation.get("node_type") or conversation.node_type
        conversation.class_name = validation.get("class_name") or conversation.class_name
        conversation.validation_status = "valid" if validation["valid"] else "invalid"
        conversation.validation_errors = validation.get("errors")
        conversation.updated_at = datetime.utcnow()
        db.commit()

        conversation_detail = ConversationDetail(
            id=conversation.id,
            title=conversation.title,
            status=conversation.status,
            provider=conversation.provider,
            model=conversation.model,
            temperature=conversation.temperature,
            requirements=conversation.requirements,
            generated_code=conversation.generated_code,
            node_type=conversation.node_type,
            class_name=conversation.class_name,
            validation_status=conversation.validation_status,
            validation_errors=conversation.validation_errors,
            message_count=conversation.message_count,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            completed_at=conversation.completed_at,
        )
        return UpdateConversationCodeResponse(success=True, conversation=conversation_detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to update conversation code: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update conversation code: {str(e)}")


