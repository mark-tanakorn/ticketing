# 🔬 TAV Engine - Visual Workflow Automation

**Build automation workflows with a drag-and-drop interface.** Connect nodes, run AI tasks, process data, and automate anything—all locally.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)

---

## ⚡ Quick Start

```bash
git clone https://github.com/Markepattsu/tav_opensource.git
cd tav_opensource
python scripts/native/start_native.py
```

**That's it!** Open **http://localhost:3000** after ~30 seconds.

👉 **[Full Setup Guide](QUICKSTART.md)** | **[Docker Setup](docs/deployment/docker-local.md)**

---

## ✨ Features

- **Visual Workflow Editor** — Drag-and-drop node-based canvas
- **35+ Built-in Nodes** — Input, processing, AI, control flow, and output
- **AI Integration** — OpenAI, Anthropic, DeepSeek, Google AI, and local models (Ollama)
- **Parallel Execution** — Smart dependency-based execution engine
- **Real-time Updates** — Live status streaming via SSE
- **Self-Hosted** — Your data stays on your machine
- **LAN Access** — Share workflows across your local network

---

## 🎯 Use Cases

- **Personal automation** — Automate repetitive tasks
- **Document processing** — Extract, transform, merge documents
- **AI workflows** — Chain LLM calls, build agents
- **Data pipelines** — Process and transform data
- **Learning** — Understand workflow automation concepts

---

## 📦 Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, SQLAlchemy, Pydantic |
| **Database** | SQLite (zero config) |
| **Frontend** | Next.js, React Flow, TypeScript |
| **AI** | LangChain, multiple provider support |

---

## 🗂️ Project Structure

```
tav_opensource/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/       # REST endpoints
│   │   ├── core/      # Nodes, execution engine
│   │   ├── database/  # Models & repositories
│   │   └── services/  # IMAP, SMTP, Twilio, etc.
│   └── tests/
├── ui/                # Next.js frontend
├── scripts/           # Startup scripts
├── deployment/        # Docker configs
└── docs/              # Documentation
```

---

## 📖 Documentation

| Topic | Link |
|-------|------|
| **Setup** | [QUICKSTART.md](QUICKSTART.md) |
| **Deployment** | [docs/deployment/](docs/deployment/) |
| **Architecture** | [docs/architecture/](docs/architecture/) |
| **Configuration** | [docs/configuration/](docs/configuration/) |
| **API Reference** | [docs/api/](docs/api/) |

---

## 🧪 Development

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pytest

# Frontend
cd ui
npm install
npm run dev
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

Inspired by n8n, Node-RED, and Zapier.

---

**Need Help?** Check the [documentation](docs/) or open an issue!
