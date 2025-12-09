# Multimodal Data Format Reference

This document defines the standardized data format for handling different media types in TAV workflows.

> **Architecture Overview**: See [Node Architecture](../architecture/nodes.md) for how multimodal data flows through nodes.

---

## Overview

All media types in TAV use a standardized `MediaFormat` structure. This ensures:
- Consistent data handling across all nodes
- Automatic UI rendering based on type
- Easy format conversion (base64 ↔ URL ↔ file path)
- Preserved metadata through workflow execution

---

## MediaFormat Structure

All data types use this unified structure:

```python
{
    "type": "text|image|audio|video|document",
    "format": "plain|markdown|png|jpg|mp3|wav|mp4|pdf|...",
    "data": "<actual_content>",
    "data_type": "string|base64|url|file_path",
    "metadata": {...}
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Media type: `text`, `image`, `audio`, `video`, `document` |
| `format` | string | File format: `plain`, `markdown`, `png`, `jpg`, `mp3`, `pdf`, etc. |
| `data` | string | The actual content (text, base64, URL, or file path) |
| `data_type` | string | How `data` is encoded: `string`, `base64`, `url`, `file_path` |
| `metadata` | object | Optional metadata (dimensions, duration, page count, etc.) |

### Examples

**Text:**
```json
{
    "type": "text",
    "format": "plain",
    "data": "Hello, world!",
    "data_type": "string",
    "metadata": {
        "char_count": 13,
        "word_count": 2,
        "line_count": 1
    }
}
```

**Image (base64):**
```json
{
    "type": "image",
    "format": "png",
    "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ...",
    "data_type": "base64",
    "metadata": {
        "width": 800,
        "height": 600
    }
}
```

**Image (file path):**
```json
{
    "type": "image",
    "format": "jpg",
    "data": "/path/to/image.jpg",
    "data_type": "file_path",
    "metadata": {
        "filename": "photo.jpg",
        "size_bytes": 245760
    }
}
```

**Audio (URL):**
```json
{
    "type": "audio",
    "format": "mp3",
    "data": "https://example.com/audio.mp3",
    "data_type": "url",
    "metadata": {
        "duration_seconds": 180
    }
}
```

**Document:**
```json
{
    "type": "document",
    "format": "pdf",
    "data": "data/uploads/report.pdf",
    "data_type": "file_path",
    "metadata": {
        "page_count": 10,
        "filename": "report.pdf"
    }
}
```

---

## Formatters

Use formatters to create properly structured MediaFormat data.

### TextFormatter

Format text data.

```python
from app.core.nodes.multimodal import TextFormatter

# Basic text
output = TextFormatter.format("Hello, world!")
# {
#     "type": "text",
#     "format": "plain",
#     "data": "Hello, world!",
#     "data_type": "string",
#     "metadata": {"char_count": 13, "word_count": 2, "line_count": 1}
# }

# Markdown text
output = TextFormatter.format(
    text="# Title\n\nContent here",
    format_type="markdown"
)

# With custom metadata
output = TextFormatter.format(
    text="Document content...",
    metadata={"source": "extraction", "page": 1}
)
```

**Method Signature:**
```python
@staticmethod
def format(
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
    format_type: str = "plain"  # "plain", "markdown", "html"
) -> Dict[str, Any]
```

---

### ImageFormatter

Format image data from various sources.

```python
from app.core.nodes.multimodal import ImageFormatter

# From base64
output = ImageFormatter.from_base64(
    base64_data="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ...",
    format="png",
    metadata={"width": 800, "height": 600}
)

# From URL
output = ImageFormatter.from_url(
    url="https://example.com/image.png",
    metadata={"source": "download"}
)

# From file path
output = ImageFormatter.from_file_path(
    file_path="/path/to/image.jpg",
    metadata={"original_name": "photo.jpg"}
)
```

**Methods:**

| Method | Parameters | Description |
|--------|------------|-------------|
| `from_base64()` | `base64_data`, `format="png"`, `metadata` | Create from base64 string |
| `from_url()` | `url`, `format=None`, `metadata` | Create from URL (format auto-detected) |
| `from_file_path()` | `file_path`, `format=None`, `metadata` | Create from file path (format auto-detected) |

---

### AudioFormatter

Format audio data from various sources.

```python
from app.core.nodes.multimodal import AudioFormatter

# From base64
output = AudioFormatter.from_base64(
    base64_data="...",
    format="mp3"
)

# From URL
output = AudioFormatter.from_url(
    url="https://example.com/audio.mp3"
)

# From file path
output = AudioFormatter.from_file_path(
    file_path="/path/to/audio.wav",
    metadata={"duration_seconds": 30}
)
```

**Methods:**

| Method | Parameters | Description |
|--------|------------|-------------|
| `from_base64()` | `base64_data`, `format="mp3"`, `metadata` | Create from base64 string |
| `from_url()` | `url`, `format=None`, `metadata` | Create from URL |
| `from_file_path()` | `file_path`, `format=None`, `metadata` | Create from file path |

---

### VideoFormatter

Format video data (typically from URL or file path, not base64 due to size).

```python
from app.core.nodes.multimodal import VideoFormatter

# From URL
output = VideoFormatter.from_url(
    url="https://example.com/video.mp4",
    metadata={"duration_seconds": 120}
)

# From file path
output = VideoFormatter.from_file_path(
    file_path="/path/to/video.mp4"
)
```

**Methods:**

| Method | Parameters | Description |
|--------|------------|-------------|
| `from_url()` | `url`, `format=None`, `metadata` | Create from URL |
| `from_file_path()` | `file_path`, `format=None`, `metadata` | Create from file path |

---

### DocumentFormatter

Format document data (PDF, DOCX, etc.).

```python
from app.core.nodes.multimodal import DocumentFormatter

# From base64
output = DocumentFormatter.from_base64(
    base64_data="...",
    format="pdf",
    metadata={"page_count": 10}
)

# From URL
output = DocumentFormatter.from_url(
    url="https://example.com/document.pdf"
)

# From file path
output = DocumentFormatter.from_file_path(
    file_path="/path/to/document.docx",
    metadata={"filename": "report.docx"}
)
```

**Methods:**

| Method | Parameters | Description |
|--------|------------|-------------|
| `from_base64()` | `base64_data`, `format="pdf"`, `metadata` | Create from base64 string |
| `from_url()` | `url`, `format=None`, `metadata` | Create from URL |
| `from_file_path()` | `file_path`, `format=None`, `metadata` | Create from file path |

---

## Helper Functions

### auto_format_media()

Auto-detect and format media data.

```python
from app.core.nodes.multimodal import auto_format_media

# From URL (auto-detects type and format)
result = auto_format_media("https://example.com/image.png")
# {"type": "image", "format": "png", "data": "https://...", "data_type": "url"}

# From file path
result = auto_format_media("/path/to/audio.mp3")
# {"type": "audio", "format": "mp3", "data": "/path/to/...", "data_type": "file_path"}

# From base64 with hints
result = auto_format_media(
    data="iVBORw0KG...",
    media_type="image",
    format="png"
)
```

**Signature:**
```python
def auto_format_media(
    data: Union[str, bytes, Dict[str, Any]],
    media_type: Optional[str] = None,
    format: Optional[str] = None
) -> Dict[str, Any]
```

**Auto-detection rules:**
- URLs starting with `http://` or `https://` → `data_type: "url"`
- Existing file paths → `data_type: "file_path"`
- Everything else → `data_type: "base64"`
- Media type detected from file extension or MIME type

---

### is_media_format()

Check if data is in MediaFormat structure.

```python
from app.core.nodes.multimodal import is_media_format

# Check if data is MediaFormat
if is_media_format(data):
    print(f"Type: {data['type']}, Format: {data['format']}")
else:
    print("Not MediaFormat")
```

**Signature:**
```python
def is_media_format(data: Any) -> bool
```

Returns `True` if data has all required fields: `type`, `format`, `data`, `data_type`

---

### extract_content()

Universal content extractor for any data format.

```python
from app.core.nodes.multimodal import extract_content

# Extract from MediaFormat (all types)
content = extract_content({"type": "text", "format": "plain", "data": "Hello", "data_type": "string"})
# "Hello"

content = extract_content({"type": "image", "format": "png", "data": "base64...", "data_type": "base64"})
# "base64..."

# Extract from legacy format (backward compatibility)
content = extract_content({"type": "text", "content": "Hello"})
# "Hello"

# Extract from plain string
content = extract_content("plain string")
# "plain string"

# Extract from dict with 'text' key
content = extract_content({"text": "Some text"})
# "Some text"
```

**Signature:**
```python
def extract_content(data: Any) -> Union[str, Dict[str, Any]]
```

**Supported formats (priority order):**
1. MediaFormat (new standard) - extracts `data` field
2. Legacy text format `{"type": "text", "content": "..."}` - extracts `content`
3. Dict with `text` key - extracts `text` value
4. Plain string - returns as-is
5. List/tuple - joins with spaces
6. Other - converts to string

---

### extract_media_data()

Extract raw data from MediaFormat.

```python
from app.core.nodes.multimodal import extract_media_data

media = {"type": "image", "format": "png", "data": "iVBORw0KG...", "data_type": "base64"}
raw_data = extract_media_data(media)
# "iVBORw0KG..."
```

---

## MediaFormat Class

Low-level class for creating MediaFormat objects.

```python
from app.core.nodes.multimodal import MediaFormat

# Create directly
media = MediaFormat(
    media_type="image",
    format="png",
    data="iVBORw0KG...",
    data_type="base64",
    metadata={"width": 800}
)

# Convert to dict
output = media.to_dict()

# Create from dict
media = MediaFormat.from_dict(existing_dict)
```

---

## Usage in Nodes

### Producing Data

Nodes that output data should use formatters:

```python
class ImageLoaderNode(Node):
    async def execute(self, input_data: NodeExecutionInput):
        file_path = input_data.ports.get("file")
        
        # Use formatter for standardized output
        output = ImageFormatter.from_file_path(
            file_path=file_path,
            metadata={
                "original_name": os.path.basename(file_path),
                "loaded_at": datetime.now().isoformat()
            }
        )
        
        return {"image": output}
```

### Consuming Data

Nodes that receive data should use `extract_content()`:

```python
class TextProcessorNode(Node):
    async def execute(self, input_data: NodeExecutionInput):
        # Works with any input format
        text = extract_content(input_data.ports.get("text"))
        
        # Process the text...
        processed = text.upper()
        
        # Output in standardized format
        return {"text": TextFormatter.format(processed)}
```

### Type Checking

Check data type before processing:

```python
class MediaRouterNode(Node):
    async def execute(self, input_data: NodeExecutionInput):
        media = input_data.ports.get("input")
        
        if is_media_format(media):
            media_type = media["type"]
            
            if media_type == "image":
                return await self.process_image(media)
            elif media_type == "audio":
                return await self.process_audio(media)
            elif media_type == "text":
                return await self.process_text(media)
        
        # Fallback for non-MediaFormat data
        return {"output": str(media)}
```

---

## Backward Compatibility

### Legacy Text Format

Old format (deprecated but still supported):
```json
{
    "type": "text",
    "content": "Hello world",
    "metadata": {...}
}
```

New format (preferred):
```json
{
    "type": "text",
    "format": "plain",
    "data": "Hello world",
    "data_type": "string",
    "metadata": {...}
}
```

`extract_content()` handles both formats automatically, but will log a warning for legacy format.

---

## Port Types and MediaFormat

| PortType | Expected MediaFormat Type |
|----------|--------------------------|
| `PortType.TEXT` | `type: "text"` |
| `PortType.IMAGE` | `type: "image"` |
| `PortType.AUDIO` | `type: "audio"` |
| `PortType.VIDEO` | `type: "video"` |
| `PortType.DOCUMENT` | `type: "document"` |
| `PortType.UNIVERSAL` | Any type |

---

## Best Practices

### 1. Always Use Formatters for Output
```python
# ✅ Good
return {"image": ImageFormatter.from_file_path(path)}

# ❌ Bad - inconsistent structure
return {"image": {"path": path, "type": "image"}}
```

### 2. Use extract_content() for Input
```python
# ✅ Good - handles all formats
text = extract_content(input_data.ports.get("text"))

# ❌ Bad - assumes specific structure
text = input_data.ports.get("text")["data"]
```

### 3. Include Relevant Metadata
```python
# ✅ Good - helpful metadata
ImageFormatter.from_file_path(
    path,
    metadata={
        "source": "upload",
        "original_name": filename,
        "processed": True
    }
)
```

### 4. Preserve Metadata Through Processing
```python
# ✅ Good - preserve and extend metadata
input_meta = input_data.ports.get("image", {}).get("metadata", {})
output = ImageFormatter.from_file_path(
    processed_path,
    metadata={**input_meta, "processed": True}
)
```

