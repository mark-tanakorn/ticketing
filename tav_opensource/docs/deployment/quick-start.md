# Quick Start Guide - 2 Minutes

Get TAV Engine running on your local machine in under 2 minutes without Docker.

## ⚡ Prerequisites

- **Python 3.10+** ([Download](https://www.python.org/downloads/))
- **Node.js 18+** ([Download](https://nodejs.org/))
- **5 GB** free disk space

## 🚀 Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/Markepattsu/tav_opensource.git
cd tav_opensource
```

### Step 2: Run the Native Start Script

**Windows (PowerShell or CMD):**
```bash
python scripts/native/start_native.py
```

**Linux/Mac:**
```bash
python3 scripts/native/start_native.py
```

**With custom ports:**
```bash
python scripts/native/start_native.py --backend-port 5001 --frontend-port 3001
```

### Step 3: Wait for Startup (30-60 seconds)

The script will:
- ✅ Check prerequisites
- ✅ Create Python virtual environment
- ✅ Install backend dependencies
- ✅ Initialize SQLite database
- ✅ Generate secure keys
- ✅ Install frontend dependencies
- ✅ Start both servers
- ✅ Open your browser

## 📍 Access Your Instance

Once started, open:
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:5000
- **API Docs:** http://localhost:5000/docs

The browser should open automatically!

## 🛑 Stopping TAV Engine

Press `Ctrl+C` in the terminal where it's running.

Or manually find and kill processes:

**Linux/Mac:**
```bash
ps aux | grep "uvicorn"
ps aux | grep "next"
kill <PID>
```

**Windows (PowerShell):**
```powershell
Get-Process | Where-Object {$_.ProcessName -match "python|node"} | Stop-Process
```

## 📁 What Was Created?

```
tav_opensource/
├── .env                        # Configuration (create from template)
├── backend/
│   ├── venv/                   # Python virtual environment
│   └── data/
│       └── tav_engine.db       # SQLite database
└── ui/
    └── node_modules/           # Node dependencies
```

## ⚙️ Configuration

Create a `.env` file in the **project root** from the template:

```bash
cp deployment/configs/env.unified.example .env
```

Default settings:
- **Development Mode:** Enabled (auto-login, no authentication)
- **Database:** SQLite (`backend/data/tav_engine.db`)
- **Ports:** Backend 5000, Frontend 3000

### Customize Configuration

Edit `.env` in project root:

```bash
# Custom ports
BACKEND_PORT=5001
FRONTEND_PORT=3001

# Add AI API keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Change log level
LOG_LEVEL=DEBUG
```

Restart after changes (stop with `Ctrl+C`, then run the script again).

## 🔍 Troubleshooting

### Port Already in Use

If ports 3000 or 5000 are already in use:

```bash
# Find what's using the port
lsof -i :3000
lsof -i :5000

# Kill the process
kill -9 <PID>
```

### Python Version Issues

```bash
# Check Python version
python3 --version

# Should be 3.10 or higher
# If not, install from python.org
```

### Node.js Version Issues

```bash
# Check Node version
node --version

# Should be v18 or higher
# If not, install from nodejs.org
```

### Database Locked

If you get "database is locked" errors:

```bash
# Stop all services (Ctrl+C or kill processes)

# Remove any lock files
rm backend/data/*.lock   # Linux/Mac
del backend\data\*.lock  # Windows

# Restart
python scripts/native/start_native.py
```

### Missing Dependencies

```bash
# Reinstall backend dependencies
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Reinstall frontend dependencies
cd ../ui
rm -rf node_modules
npm install
```

## 📊 Performance

Quick Start is suitable for:
- ✅ Development and testing
- ✅ Up to 50 workflows
- ✅ Up to 100 executions/day
- ✅ Single user
- ❌ Not for production

For production, see [Docker Production Guide](./docker-production.md).

## 🔄 Updating

```bash
# Stop services (Ctrl+C in the running terminal)

# Pull latest changes
git pull

# Restart
python scripts/native/start_native.py
```

## 🌐 Enabling Webhooks (Optional)

Quick Start runs on localhost, which doesn't support webhooks. To test webhooks:

### Option 1: Cloudflare Tunnel (Free)

```bash
# Install cloudflared
# Download from: https://developers.cloudflare.com/cloudflare-one/

# Start tunnel (in new terminal)
cloudflared tunnel --url http://localhost:5000

# Copy the generated URL (e.g., https://random-name.trycloudflare.com)
# Use this URL in webhook configurations
```

### Option 2: ngrok (Paid)

```bash
# Install ngrok
# Download from: https://ngrok.com/

# Start tunnel
ngrok http 5000

# Copy the URL (e.g., https://abc123.ngrok.io)
```

## 💡 Tips

1. **First Time Setup:** May take 2-3 minutes for dependency installation
2. **Subsequent Starts:** Usually under 30 seconds
3. **Logs:** Check terminal output for errors
4. **Reset Everything:** Delete `backend/venv`, `backend/data`, `ui/node_modules` and re-run

## 🎯 Next Steps

- [Create your first workflow](#)
- [Explore example workflows](#)
- [Add AI provider API keys](#)
- [Deploy to production](./docker-production.md)

---

**Need help?** Check [Troubleshooting](./troubleshooting.md) or ask on [Discord](https://discord.gg/your-server).

