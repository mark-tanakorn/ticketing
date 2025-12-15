# Built-in Nodes Reference

This document catalogs all built-in nodes available in TAV, organized by category.

> **Architecture Overview**: See [Node Architecture](../architecture/nodes.md) for how to create custom nodes.

---

## Quick Reference

| Category | Nodes | Description |
|----------|-------|-------------|
| [Triggers](#triggers) | 3 | Initiate workflow execution |
| [Input](#input) | 5 | File uploads and data entry |
| [AI](#ai) | 4 | LLM and AI processing |
| [Processing](#processing) | 8 | Document and file processing |
| [Actions](#actions) | 3 | HTTP requests and external services |
| [Communication](#communication) | 4 | Email and messaging |
| [Control](#control) | 4 | Flow control and logic |
| [Data](#data) | 4 | Data transformation and export |
| [Analytics](#analytics) | 3 | Monitoring and metrics |
| [Business](#business) | 4 | State management |
| [Output](#output) | 1 | Display and output |

---

## Triggers

Trigger nodes initiate workflow execution. They have no input ports and implement `TriggerCapability`.

### Schedule Trigger
**Type:** `schedule_trigger`  
**Category:** triggers  
**Capability:** TriggerCapability

Execute workflows on a time-based schedule.

| Config | Type | Description |
|--------|------|-------------|
| `interval_seconds` | integer | Time between triggers (default: 300) |
| `cron_expression` | string | Cron expression for complex schedules |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `output` | universal | Trigger data with timestamp |

---

### File Polling Trigger
**Type:** `file_polling_trigger`  
**Category:** triggers  
**Capability:** TriggerCapability

Monitor a folder for new or modified files.

| Config | Type | Description |
|--------|------|-------------|
| `watch_folder` | string | Folder path to monitor |
| `file_pattern` | string | Glob pattern (e.g., `*.pdf`) |
| `poll_interval` | integer | Seconds between checks |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `file` | document | Detected file in MediaFormat |
| `metadata` | universal | File metadata |

---

### Email Polling Trigger
**Type:** `email_polling_trigger`  
**Category:** triggers  
**Capability:** TriggerCapability

Monitor email inbox for new messages.

| Config | Type | Description |
|--------|------|-------------|
| `credential` | credential | Email account credential |
| `folder` | string | Folder to monitor (default: INBOX) |
| `poll_interval` | integer | Seconds between checks |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `email` | universal | Email data (subject, body, sender) |
| `attachments` | universal | List of attachments |

---

## Input

Input nodes accept data from users or external sources.

### Text Input
**Type:** `text_input`  
**Category:** input

Accept text input from users.

| Config | Type | Description |
|--------|------|-------------|
| `label` | string | Display label |
| `placeholder` | string | Placeholder text |
| `required` | boolean | Whether input is required |
| `default_value` | string | Default text |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `text` | text | User-entered text |

---

### Document Upload
**Type:** `document_upload`  
**Category:** input

Upload document files (PDF, DOCX, etc.).

| Config | Type | Description |
|--------|------|-------------|
| `accepted_types` | array | Allowed file extensions |
| `max_size_mb` | integer | Maximum file size |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `document` | document | Uploaded document in MediaFormat |
| `metadata` | universal | File metadata |

---

### Image Upload
**Type:** `image_upload`  
**Category:** input

Upload image files.

| Config | Type | Description |
|--------|------|-------------|
| `accepted_types` | array | Allowed formats (png, jpg, etc.) |
| `max_size_mb` | integer | Maximum file size |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `image` | image | Uploaded image in MediaFormat |
| `metadata` | universal | Image metadata |

---

### Audio Upload
**Type:** `audio_upload`  
**Category:** input

Upload audio files.

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `audio` | audio | Uploaded audio in MediaFormat |
| `metadata` | universal | Audio metadata |

---

### Video Upload
**Type:** `video_upload`  
**Category:** input

Upload video files.

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `video` | video | Uploaded video in MediaFormat |
| `metadata` | universal | Video metadata |

---

## AI

AI nodes leverage LLM and machine learning capabilities.

### LLM Chat
**Type:** `llm_chat`  
**Category:** ai  
**Capability:** LLMCapability

General-purpose LLM chat node.

| Config | Type | Description |
|--------|------|-------------|
| `system_prompt` | string | System instructions |
| `llm_provider` | string | AI provider (auto-injected) |
| `llm_model` | string | Model name (auto-injected) |
| `llm_temperature` | float | Temperature (auto-injected) |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `prompt` | text | User prompt |
| `context` | universal | Optional context data |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `response` | text | LLM response |
| `tokens` | universal | Token usage info |

---

### Vision LLM
**Type:** `vision_llm`  
**Category:** ai  
**Capability:** LLMCapability

Analyze images with vision-capable LLMs.

| Config | Type | Description |
|--------|------|-------------|
| `prompt` | string | Analysis instructions |
| `detail` | string | Image detail level (low/high/auto) |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `image` | image | Image to analyze |
| `images` | universal | Multiple images (array) |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `analysis` | text | Vision analysis result |

---

### Agent
**Type:** `agent`  
**Category:** ai  
**Capability:** LLMCapability

Autonomous agent with tool use capabilities.

| Config | Type | Description |
|--------|------|-------------|
| `system_prompt` | string | Agent instructions |
| `max_iterations` | integer | Maximum tool call iterations |
| `available_tools` | array | Tools the agent can use |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `task` | text | Task for the agent |
| `tools` | tools | Tool definitions |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `result` | text | Agent's final response |
| `steps` | universal | Execution trace |

---

### HuggingFace
**Type:** `huggingface`  
**Category:** ai  
**Capability:** AICapability

Run HuggingFace models locally.

| Config | Type | Description |
|--------|------|-------------|
| `model_id` | string | HuggingFace model ID |
| `task` | string | Task type (classification, etc.) |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `input` | universal | Model input |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `output` | universal | Model output |

---

## Processing

Processing nodes transform and manipulate data.

### Document Loader
**Type:** `document_loader`  
**Category:** processing  
**Capability:** PasswordProtectedFileCapability

Extract text from documents (PDF, DOCX, etc.).

**Features:**
- Extract text from entire document or specific pages
- Support for password-protected files
- Optional text chunking for LLM processing
- Handles PDF, DOCX, TXT, MD, CSV, JSON formats

| Config | Type | Description |
|--------|------|-------------|
| `extract_pages` | string | Pages to extract ("all" or "1,3,5" or "1-3") |
| `chunk_text` | boolean | Split text into chunks |
| `chunk_size` | integer | Chunk size in characters (100-10000) |
| `chunk_overlap` | integer | Overlap between chunks (0-1000) |
| `file_password` | string | Password (auto-injected) |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `file` | universal | Document to process |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `text` | universal | Extracted text |
| `metadata` | universal | Document metadata (page count, etc.) |

**Page Selection Examples:**
- `all` - Extract entire document (default)
- `1` - Extract only page 1
- `1,3,5` - Extract pages 1, 3, and 5
- `1-3` - Extract pages 1 through 3
- `1,3-5,7` - Extract pages 1, 3, 4, 5, and 7

---

### Document Merger
**Type:** `document_merger`  
**Category:** processing

Merge multiple documents into one.

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `documents` | universal | Array of documents |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `merged` | document | Merged document |

---

### File Converter
**Type:** `file_converter`  
**Category:** processing  
**Capability:** PasswordProtectedFileCapability

Convert files between formats (e.g., PDF to images).

| Config | Type | Description |
|--------|------|-------------|
| `conversion_type` | string | Conversion type (pdf_to_images, etc.) |
| `dpi` | integer | Output resolution (72-600) |
| `image_format` | string | Output format (png/jpeg) |
| `extract_pages` | string | Pages to extract ("all" or "1,3,5") |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `file` | universal | File to convert |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `files` | universal | Array of converted files |
| `first_file` | universal | First converted file |
| `metadata` | universal | Conversion metadata |

---

### Image Loader
**Type:** `image_loader`  
**Category:** processing

Load and process images.

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `image` | image | Image to load |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `image` | image | Processed image |
| `metadata` | universal | Image dimensions, format |

---

### Audio Transcriber
**Type:** `audio_transcriber`  
**Category:** processing  
**Capability:** AICapability

Transcribe audio to text.

| Config | Type | Description |
|--------|------|-------------|
| `language` | string | Audio language (auto-detect if empty) |
| `model` | string | Transcription model |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `audio` | audio | Audio to transcribe |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `text` | text | Transcription |
| `segments` | universal | Timestamped segments |

---

### CSV Reader
**Type:** `csv_reader`  
**Category:** processing

Parse CSV files.

| Config | Type | Description |
|--------|------|-------------|
| `delimiter` | string | Column delimiter |
| `has_header` | boolean | First row is header |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `file` | document | CSV file |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `data` | universal | Parsed data (list of dicts) |
| `headers` | universal | Column headers |

---

### Excel Reader
**Type:** `excel_reader`  
**Category:** processing

Read Excel files.

| Config | Type | Description |
|--------|------|-------------|
| `sheet_name` | string | Sheet to read (default: first) |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `file` | document | Excel file |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `data` | universal | Parsed data |
| `sheets` | universal | Available sheet names |

---

### File Listener
**Type:** `file_listener`  
**Category:** processing

Listen for file system events.

| Config | Type | Description |
|--------|------|-------------|
| `watch_path` | string | Path to monitor |
| `events` | array | Event types (created, modified, deleted) |

---

## Actions

Action nodes interact with external services.

### HTTP Request
**Type:** `http_request`  
**Category:** actions

Make HTTP requests to external APIs.

| Config | Type | Description |
|--------|------|-------------|
| `method` | string | HTTP method (GET, POST, etc.) |
| `url` | string | Request URL |
| `headers` | object | Request headers |
| `body` | string | Request body |
| `timeout` | integer | Timeout in seconds |
| `credential` | credential | Authentication credential |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `url` | text | Dynamic URL override |
| `body` | universal | Dynamic body override |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `response` | universal | Response data |
| `status_code` | universal | HTTP status code |
| `headers` | universal | Response headers |

---

### Search
**Type:** `search`  
**Category:** actions

Web search using search engines.

| Config | Type | Description |
|--------|------|-------------|
| `engine` | string | Search engine |
| `max_results` | integer | Maximum results |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `query` | text | Search query |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `results` | universal | Search results |

---

### Weather
**Type:** `weather`  
**Category:** actions

Get weather information.

| Config | Type | Description |
|--------|------|-------------|
| `api_key` | credential | Weather API key |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `location` | text | City or coordinates |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `weather` | universal | Weather data |

---

## Communication

Communication nodes for messaging.

### Email Composer
**Type:** `email_composer`  
**Category:** communication  
**Capability:** LLMCapability (optional)

Compose and send emails.

| Config | Type | Description |
|--------|------|-------------|
| `credential` | credential | Email account |
| `to` | string | Recipient(s) |
| `subject` | string | Email subject |
| `body` | string | Email body |
| `use_ai` | boolean | Generate content with AI |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `to` | text | Dynamic recipient |
| `content` | text | Content for AI generation |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `result` | universal | Send result |
| `message_id` | text | Sent message ID |

---

### Email Approval
**Type:** `email_approval`  
**Category:** communication

Send approval request via email.

| Config | Type | Description |
|--------|------|-------------|
| `approver_email` | string | Approver's email |
| `approval_timeout` | integer | Timeout in hours |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `approved` | universal | Approval decision |
| `comments` | text | Approver comments |

---

### WhatsApp Send
**Type:** `whatsapp_send`  
**Category:** communication

Send WhatsApp messages via Twilio. Supports custom messages and approved templates (ContentSID).

**Features:**
- Custom message mode with dynamic content
- Approved template mode (for Twilio business-verified templates)
- Media attachments (images, PDFs, documents)
- Template variable substitution
- Credential manager integration

| Config | Type | Description |
|--------|------|-------------|
| `auth_mode` | select | Credential manager or manual auth |
| `credential_id` | credential | Twilio credential |
| `to_number` | string | Recipient phone (with country code) |
| `message_mode` | select | Custom message or approved template |
| `message_body` | textarea | Message content (custom mode) |
| `content_sid` | string | Template ContentSID (template mode) |
| `content_variables` | textarea | Template variables JSON (template mode) |
| `include_media` | boolean | Attach media file |
| `media_url` | string | URL to media file |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `trigger` | signal | Trigger message send |
| `message_content` | universal | Dynamic message content |
| `media_url` | universal | Dynamic media URL |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `result` | universal | Send result with status |
| `message_sid` | text | Twilio message SID |

**Template Example:**
When using approved templates, provide the ContentSID and variables:
- Content SID: `HXabcd1234...` (from Twilio Console)
- Variables: `{"1": "John", "2": "Passport"}` (maps to template placeholders)

---

### WhatsApp Listener
**Type:** `whatsapp_listener`  
**Category:** communication  
**Capability:** TriggerCapability

Listen for incoming WhatsApp messages.

---

## Control

Control flow nodes for workflow logic.

### Decision
**Type:** `decision`  
**Category:** control

Conditional branching based on conditions.

| Config | Type | Description |
|--------|------|-------------|
| `condition` | string | JavaScript condition expression |
| `true_label` | string | Label for true branch |
| `false_label` | string | Label for false branch |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `input` | universal | Data to evaluate |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `true` | universal | True branch output |
| `false` | universal | False branch output |

---

### Loop Orchestrator
**Type:** `loop_orchestrator`  
**Category:** control

Iterate over arrays or ranges.

| Config | Type | Description |
|--------|------|-------------|
| `loop_type` | string | Type (foreach, range, while) |
| `max_iterations` | integer | Maximum iterations |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `items` | universal | Array to iterate |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `item` | universal | Current item |
| `index` | universal | Current index |
| `completed` | universal | All results |

---

### OR Node
**Type:** `ornode`  
**Category:** control

Wait for any of multiple inputs.

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `input_1` | universal | First input |
| `input_2` | universal | Second input |
| `input_3` | universal | Third input |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `output` | universal | First completed input |

---

### Virtual Time
**Type:** `virtual_time`  
**Category:** control

Simulate time progression for testing.

| Config | Type | Description |
|--------|------|-------------|
| `speed_multiplier` | float | Time acceleration factor |

---

## Data

Data transformation and export nodes.

### CSV Writer
**Type:** `csv_writer`  
**Category:** data  
**Capability:** ExportCapability

Export data to CSV files.

| Config | Type | Description |
|--------|------|-------------|
| `export_mode` | string | download or path (auto-injected) |
| `filename` | string | Output filename (auto-injected) |
| `columns` | array | Columns to export |
| `headers` | array | Custom header names |
| `delimiter` | string | Column separator |
| `include_headers` | boolean | Include header row |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `data` | universal | Data to export |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `result` | universal | Export result |
| `file` | universal | File in MediaFormat |

---

### PDF Writer
**Type:** `pdf_writer`  
**Category:** data  
**Capability:** ExportCapability, LLMCapability

Export data to PDF files.

| Config | Type | Description |
|--------|------|-------------|
| `mode` | string | create or template |
| `prompt` | string | AI prompt for content generation |
| `title` | string | Document title |
| `page_size` | string | letter, a4, legal |
| `replacements` | string | JSON for template replacements |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `data` | universal | Data to export |
| `template` | universal | PDF template (for template mode) |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `result` | universal | Export result |
| `file` | universal | File in MediaFormat |

---

### JSON Parser
**Type:** `json_parser`  
**Category:** data

Parse and transform JSON data.

| Config | Type | Description |
|--------|------|-------------|
| `json_path` | string | JSONPath expression |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `input` | universal | JSON data or string |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `output` | universal | Parsed/extracted data |

---

### CSV Value Extractor
**Type:** `csv_value_extractor`  
**Category:** data

Extract specific values from CSV data.

| Config | Type | Description |
|--------|------|-------------|
| `column` | string | Column name to extract |
| `row_index` | integer | Row index (0-based) |

---

## Analytics

Monitoring and analytics nodes.

### Metric Tracker
**Type:** `metric_tracker`  
**Category:** analytics

Track workflow metrics.

| Config | Type | Description |
|--------|------|-------------|
| `metric_name` | string | Name of the metric |
| `aggregation` | string | sum, avg, count, min, max |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `value` | universal | Metric value |

---

### Event Logger
**Type:** `event_logger`  
**Category:** analytics

Log events for auditing.

| Config | Type | Description |
|--------|------|-------------|
| `event_type` | string | Event category |
| `severity` | string | info, warning, error |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `event` | universal | Event data |

---

### Anomaly Detector
**Type:** `anomaly_detector`  
**Category:** analytics  
**Capability:** AICapability

Detect anomalies in data.

| Config | Type | Description |
|--------|------|-------------|
| `threshold` | float | Anomaly threshold |
| `method` | string | Detection method |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `data` | universal | Data to analyze |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `anomalies` | universal | Detected anomalies |
| `score` | universal | Anomaly score |

---

## Business

Business logic and state management nodes.

### State Get
**Type:** `state_get`  
**Category:** business

Read from persistent state store.

| Config | Type | Description |
|--------|------|-------------|
| `key` | string | State key |
| `default_value` | any | Default if not found |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `value` | universal | Retrieved value |
| `exists` | universal | Whether key exists |

---

### State Set
**Type:** `state_set`  
**Category:** business

Write to persistent state store.

| Config | Type | Description |
|--------|------|-------------|
| `key` | string | State key |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `value` | universal | Value to store |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `success` | universal | Operation result |

---

### State Update
**Type:** `state_update`  
**Category:** business

Update existing state value.

| Config | Type | Description |
|--------|------|-------------|
| `key` | string | State key |
| `operation` | string | Update operation (merge, increment, etc.) |

---

### State Delete
**Type:** `state_delete`  
**Category:** business

Delete from persistent state store.

| Config | Type | Description |
|--------|------|-------------|
| `key` | string | State key to delete |

---

## Output

Display and output nodes.

### Text Display
**Type:** `text_display`  
**Category:** output

Display text content in the workflow UI.

| Config | Type | Description |
|--------|------|-------------|
| `max_preview_length` | integer | Maximum characters to show |

**Input Ports:**
| Port | Type | Description |
|------|------|-------------|
| `text` | text | Text to display |

**Output Ports:**
| Port | Type | Description |
|------|------|-------------|
| `text` | text | Pass-through text |

---

## Creating Custom Nodes

To create custom nodes, see the [Node Architecture](../architecture/nodes.md) documentation.

Basic template:

```python
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

@register_node(
    node_type="my_custom_node",
    category=NodeCategory.PROCESSING,
    name="My Custom Node",
    description="Does something custom",
    icon="fa-solid fa-gear",
    version="1.0.0"
)
class MyCustomNode(Node):
    @classmethod
    def get_input_ports(cls):
        return [
            {"name": "input", "type": PortType.UNIVERSAL, "required": True}
        ]
    
    @classmethod
    def get_output_ports(cls):
        return [
            {"name": "output", "type": PortType.UNIVERSAL}
        ]
    
    @classmethod
    def get_config_schema(cls):
        return {
            "option": {
                "type": "string",
                "label": "Option",
                "default": "value"
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput):
        data = input_data.ports.get("input")
        option = self.resolve_config(input_data, "option")
        
        # Process data...
        result = data
        
        return {"output": result}
```

