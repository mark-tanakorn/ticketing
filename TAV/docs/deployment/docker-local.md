# Docker Local Guide - 3 Minutes

Run TAV Engine in Docker containers for isolated development with auto-restart capabilities.

## ⚡ Prerequisites

- **Docker** ([Download](https://www.docker.com/get-started))
- **Docker Compose v2** (included with Docker Desktop)
- **5 GB** free disk space

## 🚀 Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/Markepattsu/tav_opensource.git
cd tav_opensource
```

### Step 2: Start with Docker Compose

```bash
cd deployment/docker
docker compose -f docker-compose.local.yml up -d
```

The `-d` flag runs containers in the background (detached mode).

### Step 3: Wait for Startup (20-40 seconds)

Watch the logs:
```bash
docker compose -f docker-compose.local.yml logs -f
```

Press `Ctrl+C` to stop watching logs (containers keep running).

## 📍 Access Your Instance

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:5000
- **API Docs:** http://localhost:5000/docs

## 🛑 Managing the Deployment

### Stop Containers
```bash
cd deployment/docker
docker compose -f docker-compose.local.yml down
```

### Stop and Remove Data
```bash
docker compose -f docker-compose.local.yml down -v
```
⚠️ This deletes the database!

### Restart Containers
```bash
docker compose -f docker-compose.local.yml restart
```

### View Logs
```bash
# All services
docker compose -f docker-compose.local.yml logs -f

# Backend only
docker compose -f docker-compose.local.yml logs -f backend

# Frontend only
docker compose -f docker-compose.local.yml logs -f frontend
```

### Rebuild After Code Changes
```bash
docker compose -f docker-compose.local.yml up -d --build
```

## 📁 What Was Created?

```
Docker Containers:
├── tav-backend        # Backend API (Port 5000)
└── tav-frontend       # Frontend UI (Port 3000)

Docker Volumes:
├── backend_data       # SQLite database + uploads
└── ui_node_modules    # Node dependencies
```

## ⚙️ Configuration

### Environment Variables

Copy the template to project root:

```bash
cp deployment/configs/env.local.example .env
```

Edit `.env`:

```bash
# Custom ports (if needed)
BACKEND_PORT=5001
FRONTEND_PORT=3001

# Add AI API keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Change log level
LOG_LEVEL=DEBUG
```

Then rebuild:
```bash
docker compose -f docker-compose.local.yml up -d --build
```

### Custom Ports

Edit `deployment/docker/docker-compose.local.yml`:

```yaml
services:
  backend:
    ports:
      - "9000:5000"  # Change 9000 to your preferred port

  frontend:
    ports:
      - "4000:3000"  # Change 4000 to your preferred port
```

## 🔍 Troubleshooting

### Port Already in Use

```bash
# Check what's using the port
lsof -i :3000
lsof -i :5000

# Kill the process
kill -9 <PID>

# Or change ports in docker-compose.local.yml
```

### Container Won't Start

```bash
# View container status
docker ps -a

# View container logs
docker logs tav-backend
docker logs tav-frontend

# Remove and recreate
docker compose -f docker-compose.local.yml down
docker compose -f docker-compose.local.yml up -d --force-recreate
```

### Database Issues

```bash
# Reset database (⚠️ deletes all data)
docker compose -f docker-compose.local.yml down -v
docker compose -f docker-compose.local.yml up -d
```

### Build Failures

```bash
# Clean build
docker compose -f docker-compose.local.yml down
docker compose -f docker-compose.local.yml build --no-cache
docker compose -f docker-compose.local.yml up -d
```

### Out of Disk Space

```bash
# Clean up Docker
docker system prune -a --volumes

# Warning: This removes ALL unused Docker data
```

## 💾 Backup & Restore

### Backup Database

```bash
# Create backup
docker cp tav-backend:/app/data/tav_engine.db ./backup_$(date +%Y%m%d).db

# Verify backup
ls -lh backup_*.db
```

### Restore Database

```bash
# Stop containers
docker compose -f docker-compose.local.yml down

# Restore backup
docker cp backup_20251112.db tav-backend:/app/data/tav_engine.db

# Start containers
docker compose -f docker-compose.local.yml up -d
```

## 🔄 Updating

```bash
# Stop containers
docker compose -f docker-compose.local.yml down

# Pull latest code
git pull

# Rebuild and start
docker compose -f docker-compose.local.yml up -d --build
```

## 📊 Performance

Docker Local is suitable for:
- ✅ Development and testing
- ✅ Up to 100 workflows
- ✅ Up to 500 executions/day
- ✅ Multiple users (local network)
- ❌ Not for production (no SSL, no health monitoring)

For production, see [Docker Production Guide](./docker-production.md).

## 🌐 Enabling Webhooks

Docker Local runs on localhost. To enable webhooks, you need a public URL.

### Option 1: Cloudflare Tunnel (Free)

```bash
# Install cloudflared
# Download from: https://developers.cloudflare.com/cloudflare-one/

# Start tunnel
cloudflared tunnel --url http://localhost:5000

# Copy the URL and update .env.local:
PUBLIC_URL=https://random-name.trycloudflare.com
```

### Option 2: Use Production Deployment

For reliable webhooks, use [Docker Production](./docker-production.md) on a VPS.

## 🔧 Advanced: Hot Reload

By default, code changes require rebuild. To enable hot reload:

```yaml
# In docker-compose.local.yml
services:
  backend:
    volumes:
      - ../../backend/app:/app/app  # Mount source code
    command: uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload

  frontend:
    volumes:
      - ../../ui/src:/app/src  # Mount source code
      - ../../ui/public:/app/public
```

Now code changes apply instantly!

## 💡 Tips

1. **Container Names:** Use `tav-backend` and `tav-frontend` in Docker commands
2. **Logs:** Always check logs first when troubleshooting
3. **Clean State:** Use `down -v` to start fresh (but loses data)
4. **Resource Usage:** Docker uses ~1-2GB RAM for both containers

## 🎯 Next Steps

- [Explore the UI](#)
- [Create your first workflow](#)
- [Add AI provider keys](#)
- [Deploy to production](./docker-production.md)

---

**Need help?** Check [Troubleshooting](./troubleshooting.md) or ask on [Discord](https://discord.gg/your-server).

