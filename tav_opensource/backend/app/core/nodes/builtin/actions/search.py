"""
Search Node - Web Search with Multiple Providers

Performs web searches using configured API providers with DuckDuckGo fallback.
Supports Serper, Bing, Google PSE, and DuckDuckGo.
"""

import logging
import httpx
from typing import Dict, Any, List, Optional
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="search",
    category=NodeCategory.ACTIONS,
    name="Search",
    description="Perform web searches using Serper, Bing, Google PSE, or DuckDuckGo",
    icon="fa-solid fa-magnifying-glass",
    version="1.0.0"
)
class SearchNode(Node):
    """
    Search Node - Multi-provider web search
    
    Provider Priority:
    1. Serper.dev (Google results) - if API key configured
    2. Bing Web Search - if API key configured
    3. Google Programmable Search - if API key and CX configured
    4. DuckDuckGo - free fallback (no key required)
    
    Features:
    - Multiple search providers
    - Automatic fallback
    - Result filtering and ranking
    - Configurable result count
    - Safe search options
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "input",
                "type": PortType.UNIVERSAL,
                "display_name": "Input",
                "description": "Optional input (can extract query from text)",
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
                "display_name": "Search Results",
                "description": "Search results with titles, snippets, and URLs",
                "schema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Formatted search results as text (ready for templates)"
                        },
                        "summary": {
                            "type": "string",
                            "description": "One-line summary of search results"
                        },
                        "query": {
                            "type": "string",
                            "description": "The search query that was used"
                        },
                        "results_count": {
                            "type": "number",
                            "description": "Number of results found"
                        },
                        "provider": {
                            "type": "string",
                            "description": "Search provider used (serper, bing, duckduckgo)"
                        },
                        "results": {
                            "type": "array",
                            "description": "Raw results array (for LLM processing)",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "snippet": {"type": "string"},
                                    "url": {"type": "string"},
                                    "source": {"type": "string"}
                                }
                            }
                        },
                        "success": {
                            "type": "boolean",
                            "description": "Whether search succeeded"
                        }
                    }
                }
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "query": {
                "type": "string",
                "label": "Search Query",
                "description": "Search query to execute",
                "required": False,
                "placeholder": "e.g., latest AI trends 2024",
                "widget": "text",
                "help": "Leave empty to extract from input text"
            },
            "max_results": {
                "type": "integer",
                "widget": "number",
                "label": "Max Results",
                "description": "Maximum number of search results to return",
                "required": False,
                "default": 5,
                "min": 1,
                "max": 20
            },
            "country": {
                "type": "string",
                "label": "Country Code",
                "description": "Country code for localized results (e.g., US, UK, CA)",
                "required": False,
                "placeholder": "e.g., US",
                "widget": "text"
            },
            "safe_search": {
                "type": "select",
                "widget": "select",
                "label": "Safe Search",
                "description": "Safe search filtering level",
                "required": False,
                "options": [
                    {"label": "Moderate", "value": "moderate"},
                    {"label": "Strict", "value": "strict"},
                    {"label": "Off", "value": "off"}
                ],
                "default": "moderate"
            },
            "auto_extract_query": {
                "type": "boolean",
                "label": "Auto-Extract Query",
                "description": "Automatically extract search terms from input text",
                "required": False,
                "default": True
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Execute search node"""
        try:
            logger.info(f"🔎 Search node starting: {self.node_id}")
            
            # Get query from config or input
            query = self.resolve_config(input_data, "query", "")
            logger.debug(f"Query from config: '{query}'")
            
            # If no query in config, try to extract from input
            if not query:
                from app.core.nodes.multimodal import extract_content
                port_input = input_data.ports.get("input")
                logger.debug(f"Port input type: {type(port_input)}, value: {str(port_input)[:200]}")
                
                query = extract_content(port_input) if port_input else ""
                
                # Auto-extract if enabled
                auto_extract = self.resolve_config(input_data, "auto_extract_query", True)
                logger.debug(f"Auto-extract enabled: {auto_extract}, query before extraction: '{query[:100] if query else ''}'")
                
                if auto_extract and query:
                    query = self._extract_search_query(query)
            
            if not query:
                logger.warning("⚠️  No search query provided")
                return {
                    "output": {
                        "error": "No search query provided. Please specify a query in config or input.",
                        "success": False
                    }
                }
            
            # Get search configuration
            max_results = self.resolve_config(input_data, "max_results", 5)
            max_results = max(1, min(int(max_results), 20))  # Clamp to 1-20
            
            logger.info(f"🔍 Searching for: {query} (max {max_results} results)")
            
            # Get search API keys from settings
            api_keys = await self._get_search_api_keys()
            
            # Perform search with provider cascade
            results = await self._perform_search(query, max_results, api_keys)
            
            if not results:
                return {
                    "output": {
                        "error": "No search results found",
                        "query": query,
                        "success": False
                    }
                }
            
            logger.info(f"✅ Found {len(results)} search results")
            
            # Create a formatted text version for easy template insertion
            formatted_results = []
            for i, result in enumerate(results, 1):
                formatted_results.append(
                    f"{i}. {result.get('title', 'No title')}\n"
                    f"   {result.get('snippet', 'No description')}\n"
                    f"   URL: {result.get('url', 'No URL')}"
                )
            
            results_text = "\n\n".join(formatted_results)
            
            return {
                "output": {
                    "results": results,
                    "query": query,
                    "results_count": len(results),
                    "provider": results[0].get("source") if results else "unknown",
                    "success": True,
                    "text": results_text,  # ← NEW: Template-friendly formatted text
                    "summary": f"Found {len(results)} results for '{query}' using {results[0].get('source') if results else 'unknown'}"
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Search node error: {e}", exc_info=True)
            return {
                "output": {
                    "error": str(e),
                    "success": False
                }
            }
    
    async def _get_search_api_keys(self) -> Dict[str, Optional[str]]:
        """Get search API keys from database settings"""
        try:
            from app.database.session import SessionLocal
            from app.core.config.manager import SettingsManager
            
            db = SessionLocal()
            try:
                manager = SettingsManager(db)
                integrations = manager.get_integrations_settings()
                
                return {
                    "serper": integrations.search_serper_api_key or None,
                    "bing": integrations.search_bing_api_key or None,
                    "google_pse_key": integrations.search_google_pse_api_key or None,
                    "google_pse_cx": integrations.search_google_pse_cx or None,
                    "duckduckgo_enabled": integrations.search_duckduckgo_enabled
                }
            finally:
                db.close()
                
        except Exception as e:
            logger.warning(f"Could not load search API keys from settings: {e}")
            return {
                "serper": None,
                "bing": None,
                "google_pse_key": None,
                "google_pse_cx": None,
                "duckduckgo_enabled": True
            }
    
    async def _perform_search(
        self,
        query: str,
        max_results: int,
        api_keys: Dict[str, Optional[str]]
    ) -> List[Dict[str, Any]]:
        """Perform search with provider cascade"""
        
        # Try Serper first
        if api_keys.get("serper"):
            results = await self._search_serper(query, max_results, api_keys["serper"])
            if results:
                return results
        
        # Try Bing
        if api_keys.get("bing"):
            results = await self._search_bing(query, max_results, api_keys["bing"])
            if results:
                return results
        
        # Try Google PSE
        if api_keys.get("google_pse_key") and api_keys.get("google_pse_cx"):
            results = await self._search_google_pse(
                query, max_results,
                api_keys["google_pse_key"],
                api_keys["google_pse_cx"]
            )
            if results:
                return results
        
        # Fallback to DuckDuckGo
        if api_keys.get("duckduckgo_enabled", True):
            logger.info("🦆 Using DuckDuckGo fallback")
            results = await self._search_duckduckgo(query, max_results)
            if results:
                return results
        
        return []
    
    async def _search_serper(self, query: str, max_results: int, api_key: str) -> List[Dict[str, Any]]:
        """Search using Serper.dev (Google results)"""
        try:
            logger.info("🌐 Using Serper provider")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://google.serper.dev/search",
                    json={"q": query, "num": max_results},
                    headers={
                        "X-API-KEY": api_key,
                        "Content-Type": "application/json"
                    },
                    timeout=15.0
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("organic", [])[:max_results]:
                    results.append({
                        "title": item.get("title"),
                        "snippet": item.get("snippet") or item.get("description"),
                        "url": item.get("link") or item.get("url"),
                        "source": "serper"
                    })
                
                if not results:
                    logger.info(f"⚠️  Serper returned no results for query: {query[:100]}")
                else:
                    logger.info(f"✅ Serper returned {len(results)} results")
                
                return results
                
        except Exception as e:
            logger.warning(f"Serper search failed: {e}")
            return []
    
    async def _search_bing(self, query: str, max_results: int, api_key: str) -> List[Dict[str, Any]]:
        """Search using Bing Web Search API"""
        try:
            logger.info("🌐 Using Bing provider")
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.bing.microsoft.com/v7.0/search",
                    params={"q": query, "count": max_results},
                    headers={"Ocp-Apim-Subscription-Key": api_key},
                    timeout=15.0
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("webPages", {}).get("value", [])[:max_results]:
                    results.append({
                        "title": item.get("name"),
                        "snippet": item.get("snippet"),
                        "url": item.get("url"),
                        "source": "bing"
                    })
                
                return results
                
        except Exception as e:
            logger.warning(f"Bing search failed: {e}")
            return []
    
    async def _search_google_pse(
        self,
        query: str,
        max_results: int,
        api_key: str,
        cx: str
    ) -> List[Dict[str, Any]]:
        """Search using Google Programmable Search Engine"""
        try:
            logger.info("🌐 Using Google PSE provider")
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params={
                        "key": api_key,
                        "cx": cx,
                        "q": query,
                        "num": max_results
                    },
                    timeout=15.0
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("items", [])[:max_results]:
                    results.append({
                        "title": item.get("title"),
                        "snippet": item.get("snippet"),
                        "url": item.get("link"),
                        "source": "google_pse"
                    })
                
                return results
                
        except Exception as e:
            logger.warning(f"Google PSE search failed: {e}")
            return []
    
    async def _search_duckduckgo(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo Instant Answer API (free fallback)"""
        try:
            logger.info("🦆 Using DuckDuckGo provider")
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": query,
                        "format": "json",
                        "no_html": 1,
                        "no_redirect": 1
                    },
                    timeout=15.0
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                
                # Get direct results
                for item in data.get("Results", []):
                    if len(results) >= max_results:
                        break
                    title = item.get("Text")
                    url = item.get("FirstURL")
                    if title and url:
                        results.append({
                            "title": title,
                            "snippet": title,
                            "url": url,
                            "source": "duckduckgo"
                        })
                
                # Get related topics
                for item in data.get("RelatedTopics", []):
                    if len(results) >= max_results:
                        break
                    if "Topics" in item:
                        # Nested topics
                        for sub_item in item.get("Topics", []):
                            if len(results) >= max_results:
                                break
                            title = sub_item.get("Text")
                            url = sub_item.get("FirstURL")
                            if title and url:
                                results.append({
                                    "title": title,
                                    "snippet": title,
                                    "url": url,
                                    "source": "duckduckgo"
                                })
                    else:
                        # Direct topic
                        title = item.get("Text")
                        url = item.get("FirstURL")
                        if title and url:
                            results.append({
                                "title": title,
                                "snippet": title,
                                "url": url,
                                "source": "duckduckgo"
                            })
                
                return results
                
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return []
    
    def _extract_search_query(self, text: str) -> str:
        """Extract search query from text by removing stop words and cleaning"""
        import re
        
        # If text is way too long (>500 chars), it's probably LLM chain-of-thought or error
        if len(text) > 500:
            logger.warning(f"⚠️  Query text is too long ({len(text)} chars), truncating first 200 chars")
            text = text[:200]
        
        # Remove common LLM thinking patterns
        # Look for patterns like <think>...</think> or similar
        text = re.sub(r'</?think>.*?</think>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<think>.*', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove URLs that might be in the text
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Common stop words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "about", "as", "into", "through", "during",
            "before", "after", "above", "below", "between", "under", "again", "further",
            "then", "once", "here", "there", "when", "where", "why", "how", "all", "both",
            "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
            "only", "own", "same", "so", "than", "too", "very", "can", "will", "just",
            "could", "would", "should", "may", "might", "must"
        }
        
        # Clean text
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Tokenize and filter
        words = [
            word for word in clean_text.split()
            if word not in stop_words and len(word) > 2
        ]
        
        # Take first 8 meaningful words (increased from 6)
        query = " ".join(words[:8])
        
        # If extraction resulted in empty or very short query, use first sentence
        if not query or len(query) < 10:
            # Try to extract first sentence
            sentences = re.split(r'[.!?]\s+', text)
            if sentences:
                query = sentences[0][:100]
        
        logger.info(f"🔍 Extracted query: '{query}' (from {len(text)} char input)")
        
        return query.strip() or text[:100]  # Fallback to raw text if extraction fails


if __name__ == "__main__":
    print("Search Node - Multi-Provider Web Search")

