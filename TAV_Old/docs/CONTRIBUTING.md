# Contributing to TAV Engine

## Quick Setup

### Option 1: Native Script (Recommended)

```bash
git clone https://github.com/Markepattsu/tav_opensource.git
cd tav_opensource
python scripts/native/start_native.py
```

This automatically:
- Sets up Python virtual environment
- Installs backend dependencies
- Installs frontend dependencies
- Starts both servers

### Option 2: Docker

```bash
git clone https://github.com/Markepattsu/tav_opensource.git
cd tav_opensource
bash scripts/docker/start_local.sh
```

### Option 3: Manual Setup

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 5000
```

**Frontend (new terminal):**
```bash
cd ui
npm install
npm run dev
```

---

## Running Tests

**Backend:**
```bash
cd backend
pytest                    # Run all tests
pytest --cov=app          # With coverage
pytest tests/unit/        # Unit tests only
```

**Frontend:**
```bash
cd ui
npm test
```

---

## Code Style

**Backend (Python):**
```bash
cd backend
ruff check app/           # Lint
black app/ tests/         # Format
```

**Frontend (TypeScript):**
```bash
cd ui
npm run lint              # ESLint
npm run lint:fix          # Auto-fix
```

---

## Before Committing

1. ✅ Run tests locally
2. ✅ Ensure all tests pass
3. ✅ Run linter (fix any issues)
4. ✅ Update docs if needed

---

## Pull Request Process

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Write/update tests
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push (`git push origin feature/amazing-feature`)
7. Open Pull Request

---

## Project Structure

```
backend/app/
├── api/v1/endpoints/    # Add new endpoints here
├── core/nodes/builtin/  # Add new nodes here
├── database/models/     # Database models
├── schemas/             # Pydantic schemas
└── services/            # External service integrations
```

---

## Adding a New Node

1. Create file in `backend/app/core/nodes/builtin/{category}/`
2. Inherit from `BaseNode` (or capability mixin)
3. Define `node_id`, `name`, `category`, `inputs`, `outputs`
4. Implement `execute()` method
5. Node auto-registers on import

Example:
```python
from app.core.nodes.base import BaseNode

class MyNewNode(BaseNode):
    node_id = "my_new_node"
    name = "My New Node"
    category = "processing"
    
    inputs = [{"id": "input", "name": "Input", "type": "any"}]
    outputs = [{"id": "output", "name": "Output", "type": "any"}]
    
    async def execute(self, inputs, config):
        # Your logic here
        return {"output": inputs.get("input")}
```

---

## Need Help?

- Check existing code for patterns
- Open an issue for questions
- Look at similar nodes for examples
