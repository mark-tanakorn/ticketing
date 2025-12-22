# Native Deployment Scripts

Scripts for running TAV Engine natively (without Docker) on Windows, macOS, and Linux.

## start_native.py

The main startup script that launches both backend and frontend servers.

### Usage

**Basic startup (default ports 5000/3000):**
```bash
python start_native.py
```

**Custom ports:**
```bash
python start_native.py --backend-port 5001 --frontend-port 3001
# Or shorthand:
python start_native.py -b 5001 -f 3001
```

**Enable auto-reload (for development):**
```bash
python start_native.py --reload
# Or shorthand:
python start_native.py -r
```

### Auto-Reload Behavior

By default, **auto-reload is DISABLED** to prevent unexpected server restarts during normal operation.

- **Without `--reload`**: Backend runs stably, requires manual restart for code changes
- **With `--reload`**: Backend automatically restarts when Python files are modified

The frontend (Next.js) has its own built-in auto-reload that always works regardless of this flag.

### Why Auto-Reload is Disabled by Default

In native deployment mode, the script manages both frontend and backend as a unified service. When auto-reload is enabled and a file changes:

1. Uvicorn detects the file change
2. Backend server restarts
3. This can cause connection interruptions
4. May trigger unexpected shutdowns in some configurations

For **separate development** (running backend and frontend separately), auto-reload is typically enabled since each service is managed independently.

For **native deployment** (this script), auto-reload should only be enabled when actively developing backend code.

### Configuration Priority

Configuration is loaded in this order (later items override earlier ones):

1. Default values (5000, 3000)
2. `.env` file in project root
3. Command-line arguments

### Example .env File

Create a `.env` file in the project root:

```bash
BACKEND_PORT=5001
FRONTEND_PORT=3001
```

Then run:
```bash
python start_native.py
# Uses ports from .env file

python start_native.py -b 6000
# Overrides with 6000 for backend
```

### Features

- ✅ Auto-detects local IP for LAN access
- ✅ Configurable ports via CLI or .env
- ✅ Creates/validates Python virtual environment
- ✅ Installs missing dependencies automatically
- ✅ Graceful shutdown on Ctrl+C
- ✅ Network share support (Windows UNC paths)
- ✅ Dynamic CORS configuration
- ✅ Optional auto-reload for development

### Requirements

- Python 3.10+
- Node.js 18+
- 5 GB free disk space

### Troubleshooting

**Backend keeps restarting:**
- Check if `--reload` flag is enabled
- Disable auto-save in your IDE
- Run without `--reload` for stable operation

**Port already in use:**
```bash
# Find process using port
lsof -i :5000  # macOS/Linux
netstat -ano | findstr :5000  # Windows

# Use different port
python start_native.py -b 5001
```

**Virtual environment issues:**
- Delete `backend/venv` directory
- Re-run the script (it will recreate)

## See Also

- [Quick Start Guide](../../docs/deployment/quick-start.md)
- [Deployment Options](../../docs/deployment/README.md)

