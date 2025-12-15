# TAV Engine Documentation

Welcome to the TAV Engine documentation.

---

## 📚 Documentation Index

### **Getting Started**
- **[Quick Start](../QUICKSTART.md)** - Get running in minutes
- **[Deployment Options](deployment/README.md)** - Native, Docker Local, Docker Production

### **Configuration**
- **[Environment Variables](configuration/environment.md)** - `.env` file setup
- **[Application Settings](configuration/settings.md)** - Database-stored settings
- **[Execution Config](configuration/execution.md)** - Workflow execution settings

### **Architecture**
- **[System Overview](architecture/overview.md)** - High-level architecture
- **[Database Schema](architecture/database.md)** - Tables and relationships
- **[Node System](architecture/nodes.md)** - Node base classes and registry
- **[Execution Engine](architecture/executor.md)** - Parallel executor design

### **Reference**
- **[Built-in Nodes](reference/built-in-nodes.md)** - All 35+ node types
- **[Node Capabilities](reference/capabilities.md)** - LLM, AI, Export, Trigger mixins
- **[AI System](reference/ai-system.md)** - LangChainManager and providers
- **[Credentials](reference/credentials.md)** - Credential management & encryption
- **[Services](reference/services.md)** - IMAP, SMTP, Twilio services
- **[Variables](reference/variables.md)** - Variable resolution system
- **[Multimodal](reference/multimodal.md)** - Media format handling

### **API**
- **[REST API](api/rest.md)** - Endpoint reference
- **[Nodes API](api/nodes.md)** - Node CRUD operations
- **[Execution API](api/execution.md)** - Workflow execution
- **[Settings API](api/settings.md)** - Settings management

---

## 🚀 Quick Start

```bash
git clone https://github.com/Markepattsu/tav_opensource.git
cd tav_opensource
python scripts/native/start_native.py
```

Open **http://localhost:3000** after ~30 seconds.

---

## 🗄️ Database

TAV Engine uses **SQLite** for zero-config setup.

```bash
# Database location
backend/data/tav_engine.db

# Run migrations
cd backend
alembic upgrade head
```

---

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# With coverage
pytest --cov=app
```

---

## 🏗️ Project Structure

```
tav_opensource/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/       # REST endpoints
│   │   ├── core/      # Nodes, execution engine
│   │   ├── database/  # Models & repositories
│   │   └── services/  # External services
│   └── tests/
├── ui/                # Next.js frontend
├── scripts/           # Startup scripts
├── deployment/        # Docker configs
└── docs/              # Documentation (you are here)
```

---

## 🤝 Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for development setup.

---

## 📄 License

MIT License - see [LICENSE](../LICENSE) in project root.
