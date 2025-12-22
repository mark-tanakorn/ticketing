# AI System Reference

The TAV Engine uses LangChain as its AI integration layer, providing multi-provider LLM support with automatic fallback.

---

## LangChainManager

Central manager for all AI operations. Located at `backend/app/core/ai/manager.py`.

### Overview

```python
from app.core.ai.manager import get_langchain_manager

# Get manager instance
manager = get_langchain_manager(db)

# Get LLM for direct use
llm = manager.get_llm(provider="openai", model="gpt-4")

# Or use the high-level call methods
response = await manager.call_llm("What is 2+2?")
```

### Features

- **Multi-provider support**: OpenAI, Anthropic, Google, DeepSeek, Local (Ollama), and more
- **Automatic fallback**: If primary provider fails, automatically tries fallback provider
- **Settings from database**: Reads AI configuration from the Settings API
- **LLM caching**: Reuses LLM instances for performance
- **Vision model support**: Proper timeout handling for image-heavy requests

---

## Supported Providers

| Provider | Type | Notes |
|----------|------|-------|
| `openai` | ChatOpenAI | GPT-3.5, GPT-4, GPT-4o, etc. |
| `anthropic` | ChatAnthropic | Claude 3, Claude 3.5 |
| `google` | ChatGoogleGenerativeAI | Gemini Pro, Gemini Flash |
| `local` | ChatOllama | Any Ollama model (Llama, Mistral, etc.) |
| `deepseek` | OpenAI-compatible | DeepSeek Coder, DeepSeek Chat |
| `mistral` | ChatMistralAI | Mistral 7B, Mixtral |
| `groq` | OpenAI-compatible | Ultra-fast inference |
| `perplexity` | OpenAI-compatible | Web search integrated |
| `together` | OpenAI-compatible | Open-source model hosting |
| `replicate` | Replicate | Various hosted models |
| `cohere` | OpenAI-compatible | Command, Embed models |

---

## Core Methods

### `get_llm()`

Get a LangChain LLM instance for direct use.

```python
llm = manager.get_llm(
    provider="openai",       # Provider name (optional, uses default)
    model="gpt-4o",          # Model override (optional)
    temperature=0.7,         # Temperature override (optional)
    max_tokens=4096,         # Max tokens override (optional)
    streaming=False,         # Enable streaming (optional)
    timeout=120              # Request timeout in seconds (optional)
)

# Use with LangChain
from langchain.schema import HumanMessage
response = await llm.ainvoke([HumanMessage(content="Hello!")])
```

### `call_llm()`

Simple string-in, string-out LLM call with automatic fallback.

```python
response = await manager.call_llm(
    prompt="Summarize this text: ...",
    provider="openai",       # Optional
    model="gpt-4o",          # Optional
    temperature=0.5,         # Optional
    max_tokens=1000,         # Optional
    fallback=True            # Enable fallback (default: True)
)
```

### `call_llm_with_messages()`

Chat-style LLM call with message history. Supports vision models.

```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"}
]

response = await manager.call_llm_with_messages(
    messages=messages,
    provider="openai",
    model="gpt-4o",
    fallback=True
)
```

**Vision model example (with images):**

```python
# For OpenAI/Anthropic vision models
messages = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this image?"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
        ]
    }
]

# For Ollama vision models
messages = [
    {
        "role": "user",
        "content": "What's in this image?",
        "images": ["<base64_encoded_image>"]  # Ollama-specific format
    }
]
```

### `get_embeddings()`

Get embeddings instance for vector operations.

```python
embeddings = manager.get_embeddings(
    provider="openai",       # Optional
    model="text-embedding-3-small"  # Optional
)

# Use with LangChain
vectors = embeddings.embed_documents(["Hello", "World"])
```

---

## Provider Configuration

Providers are configured through the **Settings API** (see `docs/api/settings.md`).

### Database Schema (AI Settings)

```json
{
  "providers": {
    "my_openai": {
      "provider_type": "openai",
      "name": "OpenAI Production",
      "api_key": "sk-...",
      "base_url": "https://api.openai.com/v1",
      "default_model": "gpt-4o",
      "default_temperature": 0.7,
      "max_tokens_limit": 4096,
      "enabled": true,
      "role": "primary"
    },
    "my_local": {
      "provider_type": "local",
      "name": "Local Ollama",
      "base_url": "http://localhost:11434",
      "default_model": "llama3.2",
      "enabled": true,
      "role": "fallback",
      "fallback_priority": 1
    }
  },
  "default_temperature": 0.7,
  "default_max_tokens": 2048,
  "request_timeout": 120,
  "max_retries": 3
}
```

### Provider Roles

- **`primary`**: Default provider for all LLM calls
- **`fallback`**: Used when primary fails (sorted by `fallback_priority`)

---

## Automatic Fallback

When enabled, LangChainManager automatically tries fallback providers:

```
Primary Provider (openai)
    ↓ fails
Fallback Provider #1 (local, priority=1)
    ↓ fails
Fallback Provider #2 (anthropic, priority=2)
    ↓ fails
Raise Exception
```

**Example error handling:**

```python
try:
    response = await manager.call_llm("Hello", fallback=True)
except Exception as e:
    # Both primary and fallback failed
    logger.error(f"All providers failed: {e}")
```

---

## Integration with Nodes

Nodes with `LLMCapability` automatically get access to the AI system:

```python
from app.core.nodes.capabilities import LLMCapability

class MyAINode(BaseNode, LLMCapability):
    async def process(self, inputs, config, context):
        # Get LLM from capability
        llm = await self.get_llm(context)
        
        # Or use high-level method
        response = await self.call_llm(
            context=context,
            prompt="Hello!",
            temperature=0.5
        )
        
        return {"response": response}
```

See `docs/reference/capabilities.md` for more on `LLMCapability`.

---

## Timeouts and Retries

The AI system respects timeout and retry settings from the database:

| Setting | Default | Description |
|---------|---------|-------------|
| `request_timeout` | 120s | Timeout for LLM requests |
| `max_retries` | 3 | Number of retries on failure |

**Vision models** use adaptive timeouts:
- Connection timeout: 10s (fast fail on unreachable)
- Read timeout: Full `request_timeout` (can be long for image processing)

---

## Error Handling

Common error scenarios:

| Error | Cause | Solution |
|-------|-------|----------|
| `Provider not configured` | Provider not in settings | Add provider via Settings API |
| `Timeout` | Request took too long | Increase `request_timeout` in settings |
| `Authentication failed` | Invalid API key | Update API key in settings |
| `Model not found` | Invalid model name | Check provider's available models |

---

## Performance Tips

1. **Use caching**: LLM instances are cached by default (don't create new manager per request)
2. **Set appropriate timeouts**: Vision models need longer timeouts (120s+)
3. **Use fallback**: Configure a local Ollama as fallback for reliability
4. **Batch calls**: Use async properly to parallelize independent LLM calls

---

## Related Documentation

- [Capabilities Reference](capabilities.md) - LLMCapability mixin
- [Settings API](../api/settings.md) - Configuring AI providers
- [Node System](../architecture/nodes.md) - How nodes use AI

