# TAV Engine Architecture

## Overview

TAV Engine is a workflow automation platform designed for local/self-hosted deployments. It provides a visual node-based editor for building AI-powered automations.

---

## Core Components

### API Layer (FastAPI)
- RESTful API endpoints (`/api/v1/`)
- WebSocket connections for real-time collaboration
- Server-Sent Events (SSE) for execution streaming

### Execution Engine
- Dependency graph-based parallel execution
- Reactive scheduling (nodes run when dependencies complete)
- Configurable error handling, retries, and timeouts
- Resource pools for concurrency management

### Node System
- Composable capability mixins (LLM, AI, Export, Trigger)
- Auto-discovery and registration
- Standardized multimodal data format (MediaFormat)
- Variable resolution and templates

### AI Integration (LangChain)
- Multi-provider support (OpenAI, Anthropic, Google, Local)
- Automatic fallback between providers
- Embeddings and RAG support via LangChain

### Storage Layer
- **SQLite** - Workflows, executions, settings, credentials
- **File System** - Uploads, temp files, exports

---

## Data Flow

1. User creates workflow in visual editor
2. Workflow saved to SQLite database
3. User triggers execution (manual or via triggers)
4. Orchestrator loads workflow, builds dependency graph
5. Parallel executor runs nodes respecting dependencies
6. Results stored in database
7. Real-time updates via SSE stream

---

## Key Design Principles

- **Local-first**: No external dependencies required
- **Simple deployment**: Single process, SQLite database
- **Extensible**: Easy to add custom nodes
- **AI-native**: LLM integration built into core

---

## Documentation Map

| Area | Document | Description |
|------|----------|-------------|
| **Architecture** | [Node System](nodes.md) | How nodes work |
| | [Executor](executor.md) | Parallel execution engine |
| | [Database](database.md) | Data storage and schema |
| **API** | [Workflow API](../api/rest.md) | CRUD operations |
| | [Execution API](../api/execution.md) | Running workflows |
| | [Nodes API](../api/nodes.md) | Node discovery |
| | [Settings API](../api/settings.md) | Configuration |
| **Reference** | [Capabilities](../reference/capabilities.md) | Node capability mixins |
| | [Multimodal](../reference/multimodal.md) | MediaFormat specification |
| | [Variables](../reference/variables.md) | Variable resolution |
| | [Built-in Nodes](../reference/built-in-nodes.md) | All available nodes |
| | [AI System](../reference/ai-system.md) | LangChain integration |
| | [Credentials](../reference/credentials.md) | Credential management |
| | [Services](../reference/services.md) | Email, messaging services |

---

## Getting Started

- [Quick Start](../deployment/quick-start.md) - Get running in 5 minutes
- [Creating Workflows](../api/rest.md) - Build your first workflow
- [Custom Nodes](nodes.md) - Extend with your own nodes
