"""
AI Agent Node

Autonomous agent that can use other nodes as tools to achieve a goal.
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.capabilities import LLMCapability
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType, NodeConfiguration

# LangChain imports
from langchain.tools import StructuredTool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)


@register_node(
    node_type="ai_agent",
    category=NodeCategory.AI,
    name="AI Agent",
    description="Autonomous agent that uses connected nodes as tools to achieve a goal.",
    icon="fa-solid fa-robot",
    version="1.0.0"
)
class AIAgentNode(Node, LLMCapability):
    """
    AI Agent Node - The "Brain" of the workflow.
    
    This node can:
    1. Receive a goal (prompt)
    2. Inspect connected nodes on the 'tools' port
    3. Convert those nodes into AI Tools
    4. Plan and execute a sequence of actions using those tools
    5. Return the final result
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "context",
                "type": PortType.UNIVERSAL,
                "display_name": "Context",
                "description": "Additional context (chat history, previous results)",
                "required": False
            },
            {
                "name": "tools",
                "type": PortType.TOOLS,
                "display_name": "Tools",
                "description": "Connect other nodes here to use them as tools",
                "required": False,
                "max_connections": -1  # Allow multiple tools
            }
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "result",
                "type": PortType.TEXT,
                "display_name": "Result",
                "description": "Final answer from the agent"
            },
            {
                "name": "steps",
                "type": PortType.UNIVERSAL,
                "display_name": "Execution Steps",
                "description": "Log of agent's thought process and actions"
            },
            {
                "name": "tool_results",
                "type": PortType.UNIVERSAL,
                "display_name": "Tool Results",
                "description": "Individual results from each tool execution"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "system_prompt": {
                "type": "string",
                "label": "System Prompt",
                "description": "Define the agent's persona and constraints",
                "default": "You are a helpful AI assistant with access to tools.",
                "widget": "textarea",
                "rows": 3
            },
            "user_prompt": {
                "type": "string",
                "label": "User Prompt",
                "description": "What you want the agent to achieve. Supports variables {{node.field}}",
                "required": True,
                "widget": "textarea",
                "rows": 5,
                "placeholder": "Research the company connected in context and email the summary..."
            },
            "max_iterations": {
                "type": "integer",
                "label": "Max Iterations",
                "description": "Maximum number of steps the agent can take",
                "default": 10,
                "min": 1,
                "max": 50
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Execute the AI Agent."""
        # Resolve user prompt from config (with variable support)
        user_prompt = self.resolve_config(input_data, "user_prompt", "")
        
        context = input_data.ports.get("context")
        connected_tools = input_data.ports.get("tools", [])
        
        if not user_prompt:
            # Fallback: If config is empty, try context
            if isinstance(context, str) and context:
                user_prompt = context
                logger.info("⚠️ User prompt empty in config, using context as prompt")
            else:
                raise ValueError("Agent user prompt cannot be empty")
            
        logger.info(f"🤖 AI Agent starting. Prompt: {user_prompt[:50]}...")
        logger.info(f"🛠️ Available Tools: {len(connected_tools)} connected nodes")
        
        # 1. Convert connected nodes to LangChain Tools
        langchain_tools = []
        
        if not input_data.node_runner:
            logger.warning("⚠️ No node runner available! Agent cannot execute tools.")
        
        for node_config in connected_tools:
            # Skip if not a NodeConfiguration object (safety check)
            if not isinstance(node_config, NodeConfiguration):
                logger.warning(f"Invalid tool object received: {type(node_config)}")
                continue
                
            try:
                tool = self._create_tool_from_node(node_config, input_data.node_runner, input_data)
                langchain_tools.append(tool)
                logger.info(f"  + Registered tool: {tool.name} ({node_config.node_type})")
            except Exception as e:
                logger.error(f"Failed to create tool from node {node_config.name}: {e}")
        
        # 2. Initialize Agent
        # We use the LLM configured for this node (via LLMCapability)
        llm = self._get_langchain_manager().get_llm(
            provider=self.llm_provider,
            model=self.llm_model,
            temperature=self.llm_temperature
        )
        
        system_prompt = self.resolve_config(input_data, "system_prompt", "You are a helpful AI assistant.")
        
        # Escape curly braces in system_prompt to prevent LangChain from treating them as template variables
        # This is needed because the prompt may contain resolved variables with JSON data like {"cola": 20}
        system_prompt_escaped = str(system_prompt).replace("{", "{{").replace("}", "}}")
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt_escaped),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create Agent
        # Use create_tool_calling_agent for universal compatibility (OpenAI, Anthropic, Gemini, Ollama with tool support)
        # This uses the standard bind_tools() and tool_calls interface introduced in LangChain 0.1.15+
        agent = create_tool_calling_agent(llm, langchain_tools, prompt)
        logger.info("✅ Using tool-calling agent")
        
        # Create Executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=langchain_tools,
            verbose=True,
            max_iterations=self.resolve_config(input_data, "max_iterations", 10),
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
        
        # 3. Run Agent
        try:
            # Escape curly braces in user_prompt to prevent LangChain template variable errors
            # The user_prompt may contain resolved variables with JSON data
            user_prompt_escaped = str(user_prompt).replace("{", "{{").replace("}", "}}")
            
            # Prepare input
            agent_input = {"input": user_prompt_escaped}
            
            # Add context if available
            # Note: We can't easily inject arbitrary context into the standard OpenAI Agent
            # unless we modify the prompt template above.
            # For now, we append context to the prompt if it's complex data
            if context and user_prompt != context:
                context_str = str(context)
                if len(context_str) < 5000: # Limit context size
                    # Also escape curly braces in context
                    context_str_escaped = context_str.replace("{", "{{").replace("}", "}}")
                    agent_input["input"] = f"{user_prompt_escaped}\n\nContext:\n{context_str_escaped}"
            
            # Run!
            # We use `stream` instead of `ainvoke` to capture intermediate steps in real-time if needed,
            # but for now, let's stick to ainvoke but ensure we are getting the full output.
            
            # Force return_intermediate_steps=True in AgentExecutor
            
            result = await agent_executor.ainvoke(agent_input)
            
            output_text = result.get("output", "")
            steps = result.get("intermediate_steps", [])
            
            # DEBUG LOGGING
            logger.info(f"🔍 Raw Agent Result Keys: {list(result.keys())}")
            logger.info(f"🔍 Raw Steps Count: {len(steps)}")
            
            # Format steps for output
            formatted_steps = []
            tool_results = {}  # Collect individual tool results
            
            for action, observation in steps:
                formatted_steps.append({
                    "tool": action.tool,
                    "input": action.tool_input,
                    "log": action.log,
                    "observation": str(observation)
                })
                
                # Store tool result with tool name as key
                tool_name = action.tool
                if tool_name not in tool_results:
                    tool_results[tool_name] = []
                
                tool_results[tool_name].append({
                    "input": action.tool_input,
                    "output": str(observation)
                })
            
            logger.info(f"✅ Agent finished. Steps: {len(formatted_steps)}, Tools used: {list(tool_results.keys())}")
            
            return {
                "result": output_text,
                "steps": formatted_steps,
                "tool_results": tool_results
            }
            
        except Exception as e:
            logger.error(f"❌ Agent execution failed: {e}", exc_info=True)
            return {
                "result": f"Error: {str(e)}",
                "steps": [],
                "tool_results": {},
                "error": str(e)
            }
    
    def _create_tool_from_node(self, node_config: NodeConfiguration, node_runner, input_data: NodeExecutionInput) -> StructuredTool:
        """
        Create a LangChain tool from a TAV Node.
        
        Intelligently merges:
        1. Input ports (direct data flow)
        2. Critical config fields (credentials, settings)
        
        Args:
            node_config: Node configuration
            node_runner: Callback to execute the node
            input_data: Agent's execution input (for accessing user_id, context, etc.)
        """
        # 1. Get node class to inspect schema
        from app.core.nodes.registry import NodeRegistry
        node_class = NodeRegistry.get(node_config.node_type)
        if not node_class:
            raise ValueError(f"Unknown node type: {node_config.node_type}")
            
        # Get input ports definition
        input_ports = node_class.get_input_ports()
        
        # Get config schema to find critical fields
        config_schema = node_class.get_config_schema()
        
        # Build properties for JSON schema
        properties = {}
        required_fields = []
        
        # STEP 1: Add input ports as tool parameters
        for port in input_ports:
            name = port.get("name")
            if not name: continue
            
            # Skip universal/signal inputs that aren't meaningful parameters
            if name in ["input", "signal", "trigger"]:
                continue
                
            description = port.get("description", "")
            p_type = port.get("type", "universal")
            is_required = port.get("required", True)
            
            # Define type
            field_info = {"description": description}
            if p_type == "text":
                field_info["type"] = "string"
            elif p_type == "number":
                field_info["type"] = "number"
            elif p_type == "boolean":
                field_info["type"] = "boolean"
            else:
                field_info["type"] = "string"
            
            properties[name] = field_info
            if is_required:
                required_fields.append(name)
        
        # STEP 2: Add config fields as tool parameters
        # Automatically expose all user-configurable fields so the Agent can understand and control them
        # Only skip fields that are explicitly marked as internal/hidden
        
        for config_key, config_def in config_schema.items():
            # Skip only if explicitly marked as internal or hidden
            if config_def.get("internal", False) or config_def.get("hidden", False):
                continue
            
            field_type = config_def.get("type", "string")
            description = config_def.get("description", config_def.get("label", ""))
            placeholder = config_def.get("placeholder", "")
            help_text = config_def.get("help", "")
            
            # Build comprehensive description
            full_description = description
            if placeholder:
                # Escape curly braces in placeholder to prevent LangChain template variable errors
                # Replace { with {{ and } with }} so they're treated as literal characters
                escaped_placeholder = str(placeholder).replace("{", "{{").replace("}", "}}")
                full_description += f" (e.g., {escaped_placeholder})"
            if help_text:
                full_description += f". {help_text}"
            
            # Map to JSON schema types
            if field_type == "credential":
                # Enhance credential field with available credentials for this user
                available_creds = []
                
                # Get user_id from the Agent's execution context
                has_ctx = hasattr(self, 'execution_context')
                ctx_value = getattr(self, 'execution_context', None) if has_ctx else None
                logger.info(f"🔍 Credential lookup: hasattr={has_ctx}, context={ctx_value is not None}, context_type={type(ctx_value).__name__ if ctx_value else 'None'}")
                
                if has_ctx and ctx_value:
                    user_id = ctx_value.started_by
                    logger.info(f"🔑 Fetching credentials for user_id={user_id}")
                    if user_id:
                        try:
                            # Import here to avoid circular dependency
                            from app.database.session import get_db
                            from app.database.models.credential import Credential
                            from app.services.credential_service import decrypt_credential_data
                            
                            # Get credentials for this user
                            db = next(get_db())
                            try:
                                creds = db.query(Credential).filter(
                                    Credential.user_id == int(user_id)
                                ).all()
                                
                                # Build detailed credential descriptions
                                for cred in creds:
                                    cred_desc = f"{cred.id}: {cred.name} ({cred.service_type})"
                                    
                                    # Try to decrypt and show what fields are available
                                    try:
                                        decrypted = decrypt_credential_data(cred.encrypted_data)
                                        if decrypted:
                                            # Show all non-sensitive fields as hints
                                            # Exclude password-like fields but show everything else
                                            sensitive_keywords = ['password', 'secret', 'key', 'token', 'api_key']
                                            hints = []
                                            
                                            for field_name, field_value in decrypted.items():
                                                # Skip sensitive fields
                                                if any(keyword in field_name.lower() for keyword in sensitive_keywords):
                                                    continue
                                                
                                                # Show the field name and value for non-sensitive fields
                                                if isinstance(field_value, (str, int, bool)) and field_value:
                                                    # Truncate long values
                                                    str_value = str(field_value)
                                                    if len(str_value) > 40:
                                                        str_value = str_value[:37] + "..."
                                                    hints.append(f"{field_name}={str_value}")
                                            
                                            if hints:
                                                cred_desc += f" [{', '.join(hints)}]"
                                            else:
                                                # If all fields are sensitive or empty, just show field names
                                                field_names = [k for k in decrypted.keys()]
                                                if field_names:
                                                    cred_desc += f" [fields: {', '.join(field_names)}]"
                                    except Exception as decrypt_err:
                                        logger.debug(f"Could not decrypt credential {cred.id}: {decrypt_err}")
                                    
                                    available_creds.append(cred_desc)
                                
                                logger.info(f"✅ Found {len(available_creds)} credentials: {available_creds}")
                            finally:
                                db.close()
                        except Exception as e:
                            logger.error(f"❌ Could not fetch credentials for tool description: {e}", exc_info=True)
                else:
                    logger.warning(f"⚠️ No execution_context available when building tool schema (hasattr={has_ctx}, value={ctx_value is not None})")
                
                if available_creds:
                    cred_list = ", ".join(available_creds)
                    field_info = {
                        "type": "integer",
                        "description": f"{full_description}. Available credentials: [{cred_list}]. Choose by ID. The values shown in brackets are the non-sensitive fields available in each credential - use these to understand what the credential provides and what additional parameters you may need to supply."
                    }
                    logger.info(f"📋 credential_id description enriched with {len(available_creds)} credentials")
                else:
                    field_info = {
                        "type": "integer",
                        "description": f"{full_description} (use credential ID)"
                    }
                    logger.warning(f"⚠️ No credentials found, using generic description")
            elif field_type == "integer":
                field_info = {
                    "type": "integer",
                    "description": full_description
                }
            elif field_type == "boolean":
                field_info = {
                    "type": "boolean",
                    "description": full_description
                }
            elif field_type == "select":
                options = config_def.get("options", [])
                option_values = [opt.get("value") for opt in options if isinstance(opt, dict)]
                field_info = {
                    "type": "string",
                    "description": f"{full_description}. Options: {', '.join(option_values)}"
                }
            else:
                field_info = {"type": "string", "description": full_description}
            
            properties[config_key] = field_info
            # Don't make config fields required - they often have defaults
        
        # If no specific inputs found (e.g. simple nodes), add a dummy input so LLM has something to call
        if not properties:
             properties["query"] = {"type": "string", "description": "Input query or data for this tool"}
        
        logger.info(f"🔧 Created tool '{node_config.name}' with {len(properties)} parameters: {list(properties.keys())}")
        
        # 2. Define the execution wrapper
        async def run_node(**kwargs):
            """Execute the node with provided arguments"""
            if not node_runner:
                return "Error: Agent runtime does not support tool execution."
            
            logger.info(f"▶️ Agent calling tool '{node_config.name}' with args: {kwargs}")
            
            # Split kwargs into ports and config
            # Ports are direct inputs, config fields need to be injected into node config
            port_inputs = {}
            config_overrides = {}
            
            port_names = {p.get("name") for p in input_ports}
            config_field_names = set(config_schema.keys())
            
            for key, value in kwargs.items():
                # Skip None values (optional params not provided)
                if value is None:
                    continue
                    
                if key in port_names or key == "query":
                    port_inputs[key] = value
                elif key in config_field_names:
                    config_overrides[key] = value
                else:
                    # Default: treat as port input
                    port_inputs[key] = value
            
            logger.info(f"📥 Tool execution: ports={list(port_inputs.keys())}, config_overrides={list(config_overrides.keys())}")
            
            # If we added a dummy query but the node expects 'input', map it
            if "query" in port_inputs and "query" not in port_names:
                 if "input" in port_names:
                     port_inputs["input"] = port_inputs.pop("query")
            
            # TODO: Apply config_overrides to node execution
            # For now, we need to modify the node_config before passing to runner
            # This requires updating the executor's node_runner to accept config overrides
            
            try:
                # Execute node via runner with port inputs
                result = await node_runner(node_config.node_id, port_inputs, config_overrides)
                
                # Simplify result for LLM
                if isinstance(result, dict):
                    if "output" in result: return str(result["output"])
                    if "result" in result: return str(result["result"])
                    if "response" in result: return str(result["response"])
                
                return str(result)
                
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                return f"Error executing tool: {str(e)}"
        
        # 3. Create StructuredTool with Pydantic model
        from pydantic import create_model, Field
        from typing import Optional
        
        fields = {}
        for name, info in properties.items():
            t = str
            if info.get("type") == "number": t = float
            elif info.get("type") == "boolean": t = bool
            elif info.get("type") == "integer": t = int
            
            # Check if this is a required field (from input ports)
            # Config fields are always optional
            is_required = name in required_fields
            
            if is_required:
                # Required field - no default
                fields[name] = (t, Field(description=info["description"]))
            else:
                # Optional field - with None default
                fields[name] = (Optional[t], Field(default=None, description=info["description"]))
            
        # Class name must be valid identifier
        class_name = f"ToolSchema_{self._sanitize_tool_name(node_config.name)}"
        ArgsSchema = create_model(class_name, **fields)
        
        return StructuredTool.from_function(
            func=None,
            coroutine=run_node,
            name=self._sanitize_tool_name(node_config.name),
            description=node_config.description or f"Execute {node_config.name}",
            args_schema=ArgsSchema
        )

    def _sanitize_tool_name(self, name: str) -> str:
        """Sanitize name for LangChain tool (letters, numbers, underscores only)"""
        clean = "".join(c if c.isalnum() else "_" for c in name)
        return clean.strip("_")

