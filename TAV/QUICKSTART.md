# ⚡ Quick Start - TAV Engine

Get TAV Engine running on your machine in under **10 minutes**.

---

## 📋 Prerequisites

Before you begin, make sure you have:

- **Python 3.9+** ([Download](https://www.python.org/downloads/))
- **Node.js 20+** ([Download](https://nodejs.org/))
- **Git** ([Download](https://git-scm.com/))

**Optional:**
- **Docker** ([Download](https://www.docker.com/)) - For containerized deployment

---

## 🚀 Installation

### Choose Your Method:

- **🎯 [Method 1: One-Click Native](#method-1-one-click-native)** ← **Recommended** (Easiest!)
- **🐳 [Method 2: Docker](#method-2-docker)** (Production-like)
- **🔧 [Method 3: Manual Setup](#method-3-manual-setup)** (Advanced)

---

## Method 1: One-Click Native ⭐ Recommended

**This is the easiest way to get started!** One script does everything.

### Step 1: Clone the Repository

```bash
git clone https://github.com/Markepattsu/tav_opensource.git
cd tav_opensource
```

### Step 2: Run the Startup Script

**Windows:**
```bash
python scripts/native/start_native.py
```

**Or double-click:** `scripts/native/start_native.bat`

**Linux/Mac:**
```bash
python3 scripts/native/start_native.py
```

**That's it!** The script will:
- ✅ Check dependencies
- ✅ Set up virtual environment
- ✅ Install packages automatically
- ✅ Initialize database
- ✅ Start backend
- ✅ Start frontend
- ✅ Show you the URLs

**Wait 1-5 minutes** for everything to start up.


### You're Ready! 🎉

**You should see:**

```
✅ TAV Engine is running with dynamic IP detection!

📍 Local Access (this computer):
   Frontend:  http://localhost:3000
   Backend:   http://localhost:5000
   API Docs:  http://localhost:5000/docs

🌐 LAN Access (same WiFi network):
   Frontend:  http://192.168.x.x:3000
   Backend:   http://192.168.x.x:5000
```

**Open your browser:** 👉 **http://localhost:3000**

**To stop:** Press `Ctrl+C` in the terminal

---

## Method 2: Docker 🐳

Perfect for production-like environments or if you want isolation.

### Step 1: Clone Repository

```bash
git clone https://github.com/Markepattsu/tav_opensource.git
cd tav_opensource
```

### Step 2: Start with Docker

**Local Development:**
```bash
bash scripts/docker/start_local.sh
```

**LAN-Accessible (for network access):**
```bash
bash scripts/docker/start_lan.sh
```

*(If you are running on windows, it is recommended to run this on gitbash)*
*(Windows Remote File mounting system will not be available for Docker/Linus hosting)*

**Wait 5-20 minutess for containers to start.**

### Access

- **Frontend:** http://localhost:3000
- **Backend:** http://localhost:5000
- **API Docs:** http://localhost:5000/docs

**To stop:**
```bash
bash scripts/docker/stop.sh
```

---

## Method 3: Manual Setup 🔧

For advanced users who want full control.

### Step 1: Clone Repository

```bash
git clone https://github.com/Markepattsu/tav_opensource.git
cd tav_opensource
```

### Step 2: Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python scripts/init_db.py

# Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 5000
```

### Step 3: Frontend Setup (New Terminal)

```bash
cd ui

# Install dependencies
npm install

# Start frontend
npm run dev
```

### Access

- **Frontend:** http://localhost:3000
- **Backend:** http://localhost:5000

**To stop:** Press `Ctrl+C` in each terminal

---

## 🎯 What's Next?

### 1. Create Your First Workflow

1. Click **"New Workflow"** button
2. Drag a **"Text Input"** node onto the canvas
3. Drag an **"LLM Chat"** node onto the canvas
4. **Connect them** by dragging from the output port to input port
5. Click **"Run"** to execute

🎊 **You just ran your first workflow!**

### 2. Set Up AI Providers (Optional)

To use AI nodes, you'll need API keys:

1. Click **Settings** ⚙️ (top right)
2. Go to **"AI Providers"** tab
3. Add your **OpenAI** or **Anthropic** API key
4. Click **"Validate"** then **"Save"**

**Don't have API keys?** You can use **local AI** (Ollama) for free!  
👉 [See AI Setup Guide](docs/guides/ai-setup.md)

### 3. Explore Example Workflows

Check out working examples:
```bash
# In the project root
ls examples/
```

Import an example:
1. Click **"Import Workflow"**
2. Select an example JSON file
3. Explore how it works!

### 4. Read the Docs

- 📖 [Documentation](docs/)
- 🎓 [Tutorials](docs/tutorials/)
- 📘 [Architecture](docs/architecture/)

---

## ⚠️ Troubleshooting

### Backend won't start

**Error: "Port 5000 already in use"**
```bash
# Use a different port
uvicorn app.main:app --reload --host 0.0.0.0 --port 5001
```

**Error: "No module named 'app'"**
```bash
# Make sure you're in the backend directory
cd backend
pip install -r requirements.txt
```

**Error: "Database locked"**
- Only run ONE backend instance at a time
- SQLite doesn't support multiple connections well

---

### Frontend won't start

**Error: "Port 3000 already in use"**
```bash
# Use a different port
npm run dev -- --port 3001
```

**Error: "Cannot find module"**
```bash
# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

---

### Can't connect to backend

**Frontend shows "Connection Error"**

1. Make sure backend is running (check terminal)
2. Backend should be on `http://localhost:5000`
3. Check browser console for errors (F12)

---

### AI nodes not working

**"Provider not configured"**

1. Go to **Settings → AI Providers**
2. Add your API key for OpenAI, Anthropic, etc.
3. Click **"Validate"** to test
4. Click **"Save"**

**"Invalid API key"**
- Double-check you copied the entire key
- Make sure there are no extra spaces
- Verify key is active in your provider's dashboard

---

## 🆘 Still Stuck?

- 📖 [Full Troubleshooting Guide](docs/guides/troubleshooting.md)
- 🐛 [Report an Issue](https://github.com/YOUR_USERNAME/tav-engine/issues)
- 💬 [Ask for Help](https://github.com/YOUR_USERNAME/tav-engine/discussions)

---

## 🎓 Learning Path

**Beginner:**
1. ✅ Complete Quick Start (you are here!)
2. 📖 [Build Your First Workflow](docs/tutorials/first-workflow.md)
3. 📖 [Set Up AI Integration](docs/guides/ai-setup.md)

**Intermediate:**
4. 📖 [Explore All Nodes](docs/reference/nodes.md)
5. 📖 [Deploy Workflows](docs/deployment/)
6. 📖 [Understand Architecture](docs/architecture/)

**Advanced:**
7. 📖 [Contributing Guide](docs/CONTRIBUTING.md)
8. 📖 [Build Custom Nodes](docs/development/)

---

## 💡 Tips

- **Save often!** Use Ctrl+S (Cmd+S on Mac) to save workflows
- **Use the grid** - Enable grid snapping in settings for cleaner layouts
- **Keyboard shortcuts:**
  - `Delete` - Remove selected nodes
  - `Ctrl+Z` - Undo
  - `Ctrl+C/V` - Copy/paste nodes
- **Dark mode** - Toggle in settings if you prefer

---

## 🚀 Ready to Build?

You're all set! Start building powerful workflows with TAV Engine.

**Need inspiration?**
- Check out [example workflows](examples/)
- Browse [use cases](docs/guides/)
- Join our [community discussions](https://github.com/YOUR_USERNAME/tav-engine/discussions)

**Happy automating! 🎉**
