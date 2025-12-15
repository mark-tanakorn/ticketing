"""
Decision Node - Conditional Workflow Branching

Routes workflow execution based on LLM-evaluated conditions.
Uses LLMCapability for AI-powered decision making.
"""

import logging
from typing import Dict, Any, List, Optional
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.capabilities import LLMCapability
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="decision",
    category=NodeCategory.WORKFLOW,
    name="Decision",
    description="Conditional branching - route workflow based on LLM-evaluated conditions",
    icon="fa-solid fa-code-branch",
    version="1.0.0"
)
class DecisionNode(Node, LLMCapability):
    """
    Decision Node - AI-Powered Conditional Routing
    
    Features:
    - LLM-based condition evaluation for natural language decisions
    - Simple rule-based fallback for structured data
    - Binary branching (true/false paths)
    - Deterministic evaluation (temperature forced to 0)
    - Executor-level branch enforcement
    
    How It Works:
    1. Node receives input data (text, analysis, context, etc.)
    2. LLM evaluates the configured condition against the data
    3. Returns true/false decision with reasoning
    4. Executor routes to appropriate branch based on result
    5. Blocked branch nodes are automatically skipped
    
    Use Cases:
    - Content classification routing
    - Sentiment-based actions
    - Conditional approval flows
    - Quality control branching
    - A/B testing logic
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "input",
                "type": PortType.UNIVERSAL,
                "display_name": "Input",
                "description": "Data to evaluate (text, analysis results, context)",
                "required": False  # Can evaluate based on configuration alone
            }
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """
        Define output ports.
        
        CRITICAL: These port names are used for branch routing!
        The executor uses these names to determine which path to follow.
        """
        return [
            {
                "name": "true",
                "type": PortType.SIGNAL,
                "display_name": "True",
                "description": "Path taken when condition evaluates to true"
            },
            {
                "name": "false",
                "type": PortType.SIGNAL,
                "display_name": "False",
                "description": "Path taken when condition evaluates to false"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """
        Define configuration schema.
        
        Note: LLM config (provider, model, temperature) is auto-injected
        by the system because this node has LLMCapability.
        """
        return {
            "condition": {
                "type": "string",
                "label": "Condition to Evaluate",
                "description": "Natural language condition for LLM to evaluate",
                "required": True,
                "widget": "textarea",
                "placeholder": "e.g., 'Is this a complaint?', 'Does the text contain negative sentiment?', 'Is the score above 0.8?'",
                "default": "",
                "rows": 4,
                "help": "Write a natural language question or condition. The LLM will evaluate it and return true/false."
            },
            "evaluation_mode": {
                "type": "select",
                "widget": "select",
                "label": "Evaluation Mode",
                "description": "How to evaluate the condition",
                "required": False,
                "options": [
                    {"label": "Intelligent (LLM)", "value": "intelligent"},
                    {"label": "Simple (Rule-based)", "value": "simple"}
                ],
                "default": "intelligent",
                "help": "Intelligent mode uses LLM for natural language evaluation. Simple mode uses basic pattern matching."
            },
            "include_reasoning": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Include Reasoning",
                "description": "Include LLM's reasoning in output",
                "required": False,
                "default": True,
                "help": "If enabled, the node will output the LLM's reasoning for the decision."
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Execute decision node with branching logic"""
        try:
            # Resolve configuration
            condition = self.resolve_config(input_data, "condition", "")
            evaluation_mode = self.resolve_config(input_data, "evaluation_mode", "intelligent")
            include_reasoning = self.resolve_config(input_data, "include_reasoning", True)
            
            # Validate condition
            if not condition or not condition.strip():
                raise ValueError("Condition cannot be empty")
            
            # Get input data from ports
            port_input = input_data.ports.get("input", {})
            
            logger.info(
                f"🤔 Decision Node evaluating:\n"
                f"  Condition: {condition}\n"
                f"  Mode: {evaluation_mode}\n"
                f"  Has Input: {bool(port_input)}"
            )
            
            # Evaluate condition based on mode
            if evaluation_mode == "intelligent":
                decision_result = await self._evaluate_intelligent(condition, port_input, input_data)
            else:
                decision_result = self._evaluate_simple(condition, port_input)
            
            # Extract result
            meets_condition = decision_result.get("meets_condition", False)
            reasoning = decision_result.get("reasoning", "No reasoning provided")
            confidence = decision_result.get("confidence", 0.0)
            
            # Determine active path
            active_path = "true" if meets_condition else "false"
            blocked_path = "false" if meets_condition else "true"
            
            logger.info(
                f"📋 Decision result: {meets_condition} (active: {active_path})\n"
                f"💭 Reasoning: {reasoning[:100]}{'...' if len(reasoning) > 100 else ''}"
            )
            
            # Build rich decision details to attach to signal ports
            decision_details = {
                "decision_result": meets_condition,
                "result": "true" if meets_condition else "false",
                "condition": condition,
                "evaluation_mode": evaluation_mode,
                "confidence": confidence,
                "active_path": active_path
            }
            
            # Include reasoning if configured
            if include_reasoning:
                decision_details["reasoning"] = reasoning
            
            # Build output with branching control
            # The true/false ports now contain rich data, not just boolean
            output = {
                # Core decision fields (used by executor for routing)
                "decision_result": meets_condition,
                "active_path": active_path,
                "blocked_outputs": [blocked_path],
                "active_outputs": [active_path],
                
                # Port outputs - now contain full details, not just boolean
                "true": decision_details if meets_condition else {"skipped": True, "reason": "Condition evaluated to false"},
                "false": decision_details if not meets_condition else {"skipped": True, "reason": "Condition evaluated to true"},
                
                # Details port (contains all metadata)
                "details": decision_details,
                
                # Metadata (backward compatibility)
                "condition": condition,
                "evaluation_mode": evaluation_mode,
                "confidence": confidence
            }
            
            # Also include reasoning at top level if configured
            if include_reasoning:
                output["reasoning"] = reasoning
            
            return output
            
        except Exception as e:
            logger.error(f"❌ Decision node error: {e}", exc_info=True)
            
            # On error, default to false path (fail-safe)
            error_msg = str(e)
            error_details = {
                "decision_result": False,
                "result": "false",
                "condition": condition if 'condition' in locals() else "unknown",
                "evaluation_mode": evaluation_mode if 'evaluation_mode' in locals() else "unknown",
                "confidence": 0.0,
                "active_path": "false",
                "error": error_msg,
                "reasoning": f"Error during evaluation: {error_msg}"
            }
            
            return {
                "decision_result": False,
                "active_path": "false",
                "blocked_outputs": ["true"],
                "active_outputs": ["false"],
                "true": {"skipped": True, "reason": "Decision error - defaulted to false"},
                "false": error_details,
                "condition": condition if 'condition' in locals() else "unknown",
                "evaluation_mode": evaluation_mode if 'evaluation_mode' in locals() else "unknown",
                "confidence": 0.0,
                "error": error_msg,
                "reasoning": f"Error during evaluation: {error_msg}",
                "details": error_details
            }
    
    async def _evaluate_intelligent(
        self,
        condition: str,
        input_data: Any,
        node_input: NodeExecutionInput
    ) -> Dict[str, Any]:
        """
        Evaluate condition using LLM.
        
        Uses LLMCapability with temperature forced to 0 for deterministic results.
        """
        try:
            # Build evaluation prompt
            system_prompt = """You are a precise decision evaluator. Your task is to evaluate a condition against provided data.

Rules:
1. Analyze the input data carefully
2. Evaluate if the condition is met
3. Return your decision on the first line: ONLY "TRUE" or "FALSE" (all caps, nothing else)
4. On the second line, provide brief reasoning

Example response format:
TRUE
The document contains complaint-related language and expresses dissatisfaction."""

            # Format input data for LLM
            data_context = self._format_data_for_llm(input_data)
            
            user_prompt = f"""Condition to evaluate: {condition}

Input data:
{data_context}

Evaluate if the condition is met. Reply with TRUE or FALSE on the first line, then provide your reasoning."""
            
            logger.debug(f"Decision node LLM prompt:\n{user_prompt[:200]}...")
            
            # Call LLM with temperature 0 for deterministic evaluation
            # Note: The LLMCapability will handle the config automatically
            response = await self.call_llm(
                user_prompt=user_prompt,
                system_prompt=system_prompt
            )
            
            logger.info(f"Decision node LLM response: {response[:200]}...")
            
            # Parse response
            return self._parse_llm_response(response)
            
        except Exception as e:
            logger.error(f"❌ Intelligent evaluation failed: {e}", exc_info=True)
            return self._evaluate_simple(condition, input_data)
    
    def _evaluate_simple(self, condition: str, input_data: Any) -> Dict[str, Any]:
        """
        Simple rule-based condition evaluation.
        
        Supports:
        - Direct boolean values (True/False)
        - Variable references {{node.output}}
        - Keyword matching
        - Score thresholds
        - Classification labels
        """
        try:
            condition_lower = condition.lower().strip()
            meets_condition = False
            reasoning = "Simple rule-based evaluation: "
            
            # Convert input to dict if possible
            data_dict = self._normalize_input_data(input_data)
            
            # Strategy 0: Direct boolean check (HIGHEST PRIORITY)
            # Check if input is a boolean or the condition is just "true"/"false"
            if isinstance(input_data, bool):
                meets_condition = input_data
                reasoning += f"Direct boolean value: {input_data}"
                return {
                    "meets_condition": meets_condition,
                    "reasoning": reasoning,
                    "confidence": 1.0
                }
            
            # Check if condition is just a variable reference that should be treated as boolean
            if condition_lower in ['true', 'false', 'yes', 'no']:
                meets_condition = condition_lower in ['true', 'yes']
                reasoning += f"Boolean keyword: {condition_lower}"
                return {
                    "meets_condition": meets_condition,
                    "reasoning": reasoning,
                    "confidence": 1.0
                }
            
            # Check if input_data is dict with a truthy value
            if isinstance(data_dict, dict):
                # Look for common boolean fields
                for key in ['value', 'result', 'success', 'continue', 'continue_loop']:
                    if key in data_dict:
                        val = data_dict[key]
                        if isinstance(val, bool):
                            meets_condition = val
                            reasoning += f"Found boolean field '{key}': {val}"
                            return {
                                "meets_condition": meets_condition,
                                "reasoning": reasoning,
                                "confidence": 1.0
                            }
            
            # Strategy 1: Check for classification data
            if isinstance(data_dict, dict):
                # Look for classification results
                classification = (
                    data_dict.get("classification") or
                    data_dict.get("analysis", {}).get("classification") or
                    {}
                )
                
                if classification:
                    # Check if condition keywords match classification labels
                    for label, score in classification.items():
                        label_lower = label.lower()
                        
                        # Direct keyword match
                        if any(word in label_lower for word in condition_lower.split()):
                            if isinstance(score, (int, float)) and score > 0.5:
                                meets_condition = True
                                reasoning += f"Found matching label '{label}' with score {score:.2f}"
                                break
                
                # Strategy 2: Check for boolean/sentiment patterns
                if not meets_condition:
                    # Check for sentiment keywords
                    if any(word in condition_lower for word in ['positive', 'good', 'happy']):
                        sentiment_score = self._extract_sentiment_score(data_dict, positive=True)
                        if sentiment_score and sentiment_score > 0.5:
                            meets_condition = True
                            reasoning += f"Positive sentiment detected (score: {sentiment_score:.2f})"
                    
                    elif any(word in condition_lower for word in ['negative', 'bad', 'complaint', 'unhappy']):
                        sentiment_score = self._extract_sentiment_score(data_dict, positive=False)
                        if sentiment_score and sentiment_score > 0.5:
                            meets_condition = True
                            reasoning += f"Negative sentiment detected (score: {sentiment_score:.2f})"
                
                # Strategy 3: Check for score/threshold conditions
                if not meets_condition and any(op in condition_lower for op in ['>', '<', 'above', 'below', 'greater', 'less']):
                    meets_condition = self._evaluate_threshold(condition_lower, data_dict)
                    reasoning += "Evaluated threshold condition"
            
            # Strategy 4: Check for "contains" text matching
            if not meets_condition and "contains" in condition_lower:
                # Extract the keyword after "contains"
                search_term = condition_lower.replace("contains", "").strip()
                
                # Check if search term appears in the input text
                input_text = ""
                if isinstance(input_data, str):
                    input_text = input_data.lower()
                elif isinstance(data_dict, dict) and "text" in data_dict:
                    input_text = str(data_dict["text"]).lower()
                
                if search_term and search_term in input_text:
                    meets_condition = True
                    reasoning += f"Text contains '{search_term}'"
            
            # Strategy 5: Fallback to simple keyword matching
            if not meets_condition:
                if any(word in condition_lower for word in ['true', 'yes', 'positive', 'pass']):
                    meets_condition = True
                    reasoning += "Keyword match (true/yes/positive)"
                else:
                    reasoning += "No matching patterns found, defaulting to false"
            
            return {
                "meets_condition": meets_condition,
                "reasoning": reasoning,
                "confidence": 0.7  # Lower confidence for simple evaluation
            }
            
        except Exception as e:
            logger.error(f"❌ Simple evaluation failed: {e}")
            return {
                "meets_condition": False,
                "reasoning": f"Evaluation error: {str(e)}",
                "confidence": 0.0
            }
    
    def _format_data_for_llm(self, data: Any) -> str:
        """Format input data for LLM consumption"""
        if isinstance(data, str):
            return data
        elif isinstance(data, dict):
            # Pretty format dict
            import json
            try:
                return json.dumps(data, indent=2, default=str)
            except:
                return str(data)
        elif isinstance(data, (list, tuple)):
            import json
            try:
                return json.dumps(data, indent=2, default=str)
            except:
                return str(data)
        else:
            return str(data)
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response to extract decision and reasoning"""
        try:
            # Clean response
            response = response.strip()
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            
            if not lines:
                logger.warning("Empty LLM response")
                return {
                    "meets_condition": False,
                    "reasoning": "Empty response from LLM",
                    "confidence": 0.0
                }
            
            # First line should be the decision
            decision_line = lines[0].upper()
            
            # Look for TRUE/FALSE in the first line
            if "TRUE" in decision_line:
                meets_condition = True
            elif "FALSE" in decision_line:
                meets_condition = False
            else:
                # Fallback: look for positive/negative language
                decision_lower = decision_line.lower()
                meets_condition = any(word in decision_lower for word in ['yes', 'correct', 'matches', 'meets', 'is'])
                logger.warning(f"Ambiguous decision line: {decision_line}, interpreting as {meets_condition}")
            
            # Extract reasoning (everything after first line)
            reasoning = '\n'.join(lines[1:]) if len(lines) > 1 else decision_line
            
            logger.info(f"Parsed decision: {meets_condition}, reasoning: {reasoning[:100]}...")
            
            return {
                "meets_condition": meets_condition,
                "reasoning": reasoning or "Decision made",
                "confidence": 0.95  # High confidence for LLM evaluation
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to parse LLM response: {e}")
            return {
                "meets_condition": False,
                "reasoning": f"Failed to parse response: {str(e)}",
                "confidence": 0.0
            }
    
    def _normalize_input_data(self, data: Any) -> Dict[str, Any]:
        """Normalize various input formats to dict"""
        if isinstance(data, dict):
            return data
        elif isinstance(data, str):
            return {"text": data}
        elif isinstance(data, (list, tuple)):
            return {"items": list(data)}
        else:
            return {"value": str(data)}
    
    def _extract_sentiment_score(self, data: Dict[str, Any], positive: bool = True) -> Optional[float]:
        """Extract sentiment score from various data formats"""
        try:
            # Check for sentiment in various locations
            sentiment_data = (
                data.get("sentiment") or
                data.get("analysis", {}).get("sentiment") or
                {}
            )
            
            if isinstance(sentiment_data, dict):
                # Look for positive/negative scores
                if positive:
                    return sentiment_data.get("positive") or sentiment_data.get("pos")
                else:
                    return sentiment_data.get("negative") or sentiment_data.get("neg")
            elif isinstance(sentiment_data, (int, float)):
                # Numeric sentiment (-1 to 1 or 0 to 1)
                if positive:
                    return max(0, sentiment_data)
                else:
                    return max(0, -sentiment_data)
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not extract sentiment: {e}")
            return None
    
    def _evaluate_threshold(self, condition: str, data: Dict[str, Any]) -> bool:
        """Evaluate threshold conditions like 'score > 0.8'"""
        try:
            import re
            
            # Extract number from condition
            numbers = re.findall(r'\d+\.?\d*', condition)
            if not numbers:
                return False
            
            threshold = float(numbers[0])
            
            # Find scores in data
            scores = []
            for key, value in data.items():
                if 'score' in key.lower() or 'confidence' in key.lower():
                    if isinstance(value, (int, float)):
                        scores.append(value)
                    elif isinstance(value, dict):
                        scores.extend([v for v in value.values() if isinstance(v, (int, float))])
                # Also check inside classification dicts
                elif key.lower() == 'classification' and isinstance(value, dict):
                    scores.extend([v for v in value.values() if isinstance(v, (int, float))])
            
            if not scores:
                return False
            
            # Evaluate based on operator
            max_score = max(scores)
            if any(op in condition for op in ['>', 'above', 'greater']):
                return max_score > threshold
            elif any(op in condition for op in ['<', 'below', 'less']):
                return max_score < threshold
            
            return False
            
        except Exception as e:
            logger.debug(f"Could not evaluate threshold: {e}")
            return False


if __name__ == "__main__":
    # Example usage
    print("Decision Node - Conditional Workflow Branching")

