"""
Custom Nodes - tooling endpoints (read-only lookup + curated examples).

Split out from endpoints/custom_nodes.py to keep modules small.
"""

import logging
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_smart, get_db
from app.api.v1.schemas.custom_nodes import (
    ExampleRequest,
    ExampleResponse,
    ToolLookupRequest,
    ToolLookupResponse,
    ToolLookupResult,
)
from app.database.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


ALLOWED_SCOPES = {
    "builtin": Path("app/core/nodes/builtin"),
    "base": Path("app/core/nodes/base.py"),
    "registry": Path("app/core/nodes/registry.py"),
    "loader": Path("app/core/nodes/loader.py"),
    "docs": Path("docs/reference/built-in-nodes.md"),
}


def _safe_read(path: Path, max_bytes: int = 8000) -> str:
    """Read file content safely, bounded by max_bytes."""
    if not path.exists() or not path.is_file():
        return ""
    data = path.read_bytes()[:max_bytes]
    return data.decode(errors="ignore")


def _search_in_dir(root: Path, query: str, max_results: int) -> List[ToolLookupResult]:
    results: List[ToolLookupResult] = []
    query_lower = (query or "").lower()
    for file in sorted(root.rglob("*.py")):
        if len(results) >= max_results:
            break
        try:
            text = file.read_text(errors="ignore")
            if query_lower and query_lower in text.lower():
                idx = text.lower().find(query_lower)
                start = max(0, idx - 200)
                end = min(len(text), idx + 200)
                snippet = text[start:end]
                results.append(ToolLookupResult(path=str(file), snippet=snippet))
        except Exception:
            continue
    return results


@router.post("/tools/lookup", response_model=ToolLookupResponse)
async def tool_lookup(
    request: ToolLookupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart),
):
    """
    Read-only lookup across bounded scopes:
    - builtin : app/core/nodes/builtin/**
    - base    : app/core/nodes/base.py
    - registry: app/core/nodes/registry.py
    - loader  : app/core/nodes/loader.py
    - docs    : docs/reference/built-in-nodes.md
    """
    _ = db, current_user
    scope = request.scope.lower()
    if scope not in ALLOWED_SCOPES:
        raise HTTPException(status_code=400, detail="Invalid scope")

    root = ALLOWED_SCOPES[scope]
    results: List[ToolLookupResult] = []

    if root.is_file():
        content = _safe_read(root)
        if not content:
            return ToolLookupResponse(success=False, results=[])
        if request.query.strip():
            q = request.query.lower()
            if q in content.lower():
                idx = content.lower().find(q)
                start = max(0, idx - 200)
                end = min(len(content), idx + 200)
                snippet = content[start:end]
            else:
                snippet = content[: min(len(content), 800)]
        else:
            snippet = content[: min(len(content), 800)]
        results.append(ToolLookupResult(path=str(root), snippet=snippet))
    else:
        results = _search_in_dir(root, request.query, request.max_results)

    return ToolLookupResponse(success=True, results=results)


EXAMPLES: Dict[str, str] = {
    "llm": """```python
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType
from app.services.langchain_manager import LangChainManager

@register_node(
    node_type="llm_prompt",
    category=NodeCategory.AI,
    name="LLM Prompt",
    description="Call an LLM with a prompt",
    icon="fa-solid fa-robot",
)
class LLMPromptNode(Node):
    @classmethod
    def get_input_ports(cls):
        return [{
            "name": "prompt",
            "type": PortType.TEXT,
            "display_name": "Prompt",
            "description": "Prompt to send",
            "required": True,
        }]

    @classmethod
    def get_output_ports(cls):
        return [{
            "name": "response",
            "type": PortType.TEXT,
            "display_name": "Response",
            "description": "LLM response",
            "required": True,
        }]

    @classmethod
    def get_config_schema(cls):
        return {
            "provider": {"type": "text", "label": "Provider", "default": "anthropic"},
            "model": {"type": "text", "label": "Model", "default": "claude-3-5-sonnet-20241022"},
            "temperature": {"type": "number", "label": "Temperature", "default": 0.2},
        }

    async def execute(self, input_data: NodeExecutionInput):
        manager = LangChainManager(self.db)  # assumes db available on self
        prompt = input_data.inputs.get("prompt", "")
        result = await manager.call_llm(
            prompt=prompt,
            provider=self.config.get("provider", "anthropic"),
            model=self.config.get("model", "claude-3-5-sonnet-20241022"),
            temperature=float(self.config.get("temperature", 0.2)),
        )
        return {"response": result}
```""",
    "http": """```python
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType
import requests

@register_node(
    node_type="http_get",
    category=NodeCategory.ACTIONS,
    name="HTTP GET",
    description="Fetch JSON from a URL",
    icon="fa-solid fa-globe",
)
class HttpGetNode(Node):
    @classmethod
    def get_input_ports(cls):
        return [{
            "name": "trigger",
            "type": PortType.SIGNAL,
            "display_name": "Trigger",
            "description": "Trigger request",
            "required": False,
        }]

    @classmethod
    def get_output_ports(cls):
        return [{
            "name": "data",
            "type": PortType.UNIVERSAL,
            "display_name": "Data",
            "description": "Response JSON",
            "required": True,
        }]

    @classmethod
    def get_config_schema(cls):
        return {
            "url": {"type": "text", "label": "URL", "required": True, "default": "https://api.example.com/data"},
            "timeout": {"type": "number", "label": "Timeout (s)", "default": 10},
        }

    async def execute(self, input_data: NodeExecutionInput):
        url = self.config.get("url")
        timeout = float(self.config.get("timeout", 10))
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return {"data": resp.json()}
```""",
    "processing": """```python
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

@register_node(
    node_type="text_uppercase",
    category=NodeCategory.PROCESSING,
    name="Text Uppercase",
    description="Convert text to uppercase",
    icon="fa-solid fa-arrows-up-to-line",
)
class TextUppercaseNode(Node):
    @classmethod
    def get_input_ports(cls):
        return [{
            "name": "text",
            "type": PortType.TEXT,
            "display_name": "Text",
            "description": "Input text",
            "required": True,
        }]

    @classmethod
    def get_output_ports(cls):
        return [{
            "name": "result",
            "type": PortType.TEXT,
            "display_name": "Uppercase Text",
            "description": "Uppercased text",
            "required": True,
        }]

    @classmethod
    def get_config_schema(cls):
        return {}

    async def execute(self, input_data: NodeExecutionInput):
        text = input_data.inputs.get("text", "")
        return {"result": text.upper()}
```""",
    "export": """```python
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType
import json

@register_node(
    node_type="json_export",
    category=NodeCategory.EXPORT,
    name="JSON Export",
    description="Serialize data to JSON string",
    icon="fa-solid fa-file-export",
)
class JsonExportNode(Node):
    @classmethod
    def get_input_ports(cls):
        return [{
            "name": "data",
            "type": PortType.UNIVERSAL,
            "display_name": "Data",
            "description": "Data to export",
            "required": True,
        }]

    @classmethod
    def get_output_ports(cls):
        return [{
            "name": "json",
            "type": PortType.TEXT,
            "display_name": "JSON",
            "description": "Serialized JSON",
            "required": True,
        }]

    @classmethod
    def get_config_schema(cls):
        return {}

    async def execute(self, input_data: NodeExecutionInput):
        data = input_data.inputs.get("data")
        return {"json": json.dumps(data)}
```""",
    "weather": """```python
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType
import requests

@register_node(
    node_type="weather_fetch",
    category=NodeCategory.ACTIONS,
    name="Weather Fetch",
    description="Fetch current weather for cities",
    icon="fa-solid fa-cloud-sun",
)
class WeatherFetchNode(Node):
    @classmethod
    def get_input_ports(cls):
        return [{
            "name": "trigger",
            "type": PortType.SIGNAL,
            "display_name": "Trigger",
            "description": "Trigger fetch",
            "required": False,
        }]

    @classmethod
    def get_output_ports(cls):
        return [
            {"name": "weather_json", "type": PortType.UNIVERSAL, "display_name": "Weather JSON", "description": "Raw weather data", "required": True},
            {"name": "summary", "type": PortType.TEXT, "display_name": "Summary", "description": "Summary text", "required": True},
        ]

    @classmethod
    def get_config_schema(cls):
        return {
            "api_key": {"type": "text", "label": "API Key", "required": True, "secret": True},
            "cities": {"type": "text", "label": "Cities (comma-separated)", "default": "Singapore, Bangkok", "required": True},
            "units": {"type": "select", "label": "Units", "default": "metric",
                      "options": [{"label": "Metric", "value": "metric"}, {"label": "Imperial", "value": "imperial"}, {"label": "Standard", "value": "standard"}]},
        }

    async def execute(self, input_data: NodeExecutionInput):
        api_key = self.config.get("api_key")
        units = self.config.get("units", "metric")
        cities_str = self.config.get("cities", "")
        cities = [c.strip() for c in cities_str.split(",") if c.strip()]
        if not api_key or not cities:
            raise ValueError("API key and at least one city are required")

        base_url = "https://api.openweathermap.org/data/2.5/weather"
        results = []
        for city in cities:
            try:
                params = {"q": city, "appid": api_key, "units": units}
                resp = requests.get(base_url, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                results.append(data)
            except Exception as e:
                results.append({"city": city, "error": str(e)})

        summaries = []
        unit_symbol = "°C" if units == "metric" else ("°F" if units == "imperial" else "K")
        for r in results:
            if "error" in r:
                summaries.append(f"{r.get('city','?')}: {r['error']}")
            else:
                summaries.append(f"{r.get('name','?')}: {r.get('main',{}).get('temp','?')}{unit_symbol}, {r.get('weather',[{}])[0].get('description','')}")

        return {
            "weather_json": results,
            "summary": "\\n".join(summaries),
        }
```""",
}


@router.post("/tools/example", response_model=ExampleResponse)
async def tool_example(
    request: ExampleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart),
):
    """Return a curated example snippet by kind."""
    _ = db, current_user
    kind = request.kind.lower()
    if kind not in EXAMPLES:
        raise HTTPException(status_code=400, detail="Invalid example kind")
    return ExampleResponse(success=True, example=EXAMPLES[kind])


