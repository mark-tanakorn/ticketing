# TAV Engine - Docker Deployment Guide

Quick setup guide for TAV Engine using Docker. Choose the deployment that fits your needs.

## 🎯 Quick Start - Choose Your Setup

| Setup | Use Case | Setup Time | Access |
|-------|----------|------------|--------|
| **[Localhost](#1-localhost-development)** | Solo development on your computer | ~5 min | `http://localhost:3000` |
| **[LAN Access](#2-lan-access-wifi-network)** | Share with team on same WiFi | ~5-10 min | `http://192.168.x.x:3000` |
| **[Production](#3-production-internet)** | Deploy to internet with SSL | ~10-15 min | `https://yourdomain.com` |

---

## 1. Localhost Development

**Best for**: Solo development, fastest setup, testing on your own computer

### Quick Start
```bash
cd deployment/scripts
chmod +x docker-start-local.sh
./docker-start-local.sh
```

### Or Manual Start
```bash
cd deployment/docker
docker-compose up -d
```

### Access
- Frontend: http://localhost:3000
- Backend: http://localhost:5000
- API Docs: http://localhost:5000/docs

### Features
- ✅ No configuration needed
- ✅ SQLite database (no external DB)
- ✅ Hot reload for development
- ✅ Dev mode enabled (no auth)
- ✅ Works offline

---

## 2. LAN Access (WiFi Network)

**Best for**: Sharing with team, demos, testing on multiple devices

### Quick Start
```bash
cd deployment/scripts
chmod +x docker-start-lan.sh
./docker-start-lan.sh
```

The script will:
1. Auto-detect your local IP (e.g., 192.168.1.100)
2. Configure CORS for LAN access
3. Start services accessible on WiFi

### Or Manual Start
```bash
# 1. Find your local IP
ipconfig     # Windows
ifconfig     # Mac/Linux
hostname -I  # Linux

# 2. Set LAN_IP and start
cd deployment/docker
export LAN_IP=192.168.1.100  # Your actual IP
docker-compose -f docker-compose.lan.yml up -d
```

### Access
- **From your computer**: http://localhost:3000
- **From other devices**: http://192.168.1.100:3000 (use your IP)

### Features
- ✅ Accessible on local network
- ✅ Share with team on same WiFi
- ✅ Test on mobile devices
- ✅ SQLite database
- ✅ Dev mode enabled

### Security Notes
- ⚠️ Anyone on your WiFi can access
- ⚠️ Dev mode enabled (no authentication)
- ✅ Good for: Trusted networks, offices
- ❌ Bad for: Public WiFi, cafes

---

## 3. Production (Internet)

**Best for**: Real deployments, public access, production use

### Prerequisites
- Domain name (e.g., `tav.example.com`)
- SSL certificate (Let's Encrypt recommended)
- Server with public IP

### Setup Steps

#### Step 1: Create .env File
```bash
cd deployment/docker
cp ../configs/env.production.example .env
nano .env  # Edit with your values
```

Required variables:
```env
DOMAIN=tav.example.com
SECRET_KEY=<generate with: openssl rand -base64 32>
ENCRYPTION_KEY=<generate with: openssl rand -base64 32>
CORS_ORIGINS=["https://tav.example.com"]
```

#### Step 2: Start Services
```bash
cd deployment/scripts
chmod +x docker-start-production.sh
./docker-start-production.sh
```

### Access
- Frontend: https://tav.example.com
- Backend: https://tav.example.com/api
- API Docs: https://tav.example.com/api/docs

### Features
- ✅ Internet-accessible
- ✅ SSL/HTTPS required
- ✅ Authentication enabled
- ✅ Production optimized
- ✅ SQLite or PostgreSQL

### Security Checklist
- ✅ Use strong SECRET_KEY and ENCRYPTION_KEY
- ✅ Enable HTTPS/SSL
- ✅ Set ENABLE_DEV_MODE=false
- ✅ Configure firewall
- ✅ Set specific CORS_ORIGINS (not "*")
- ✅ Regular backups

---

## 📋 Common Commands

### View Logs
```bash
# Localhost
docker-compose logs -f

# LAN
docker-compose -f docker-compose.lan.yml logs -f

# Production
docker-compose -f docker-compose.production.yml logs -f
```

### Stop Services
```bash
# Localhost
docker-compose down

# LAN
docker-compose -f docker-compose.lan.yml down

# Production
docker-compose -f docker-compose.production.yml down
```

### Restart Services
```bash
# Localhost
docker-compose restart

# LAN
docker-compose -f docker-compose.lan.yml restart

# Production
docker-compose -f docker-compose.production.yml restart
```

### Rebuild (after code changes)
```bash
# Localhost
docker-compose up -d --build

# LAN
docker-compose -f docker-compose.lan.yml up -d --build

# Production
docker-compose -f docker-compose.production.yml up -d --build
```

### Reset Everything
```bash
# Warning: This deletes all data!
docker-compose down -v
docker-compose up -d
```

---

## 🔧 Troubleshooting

### Services Won't Start
```bash
# Check Docker is running
docker info

# Check logs for errors
docker-compose logs

# Check port conflicts
netstat -an | grep :3000
netstat -an | grep :5000
```

### Can't Access from LAN
1. Check firewall allows ports 3000 and 5000
2. Verify LAN_IP is correct
3. Make sure both devices are on same WiFi
4. Try from another device: `http://YOUR_IP:3000`

### Database Issues
```bash
# Reset database (deletes all data!)
docker-compose down -v
docker-compose up -d
```

### CORS Errors
1. Check `CORS_ORIGINS` in environment
2. Verify using correct URL (http vs https)
3. For LAN: Make sure using IP, not localhost
4. For Production: Match domain exactly

---

## 📊 Comparison Table

| Feature | Localhost | LAN | Production |
|---------|-----------|-----|------------|
| Setup Time | 5 min | 5-10 min | 10-15 min |
| Network Access | This computer | WiFi network | Internet |
| Authentication | Disabled | Disabled | Enabled |
| SSL/HTTPS | Not needed | Not needed | Required |
| Database | SQLite | SQLite | SQLite/PostgreSQL |
| Good For | Solo dev | Team demos | Real users |
| Configuration | None | Minimal | Full |

---

## 🚀 Next Steps

After starting your deployment:

1. **Create an Admin User** (if auth is enabled)
2. **Configure AI Providers** in Settings
3. **Create Your First Workflow**
4. **Set Up Credentials** for external services
5. **Test an Execution**

---

## 📚 More Information

- Full Documentation: `/docs/`
- API Documentation: http://localhost:5000/docs
- Deployment Guides: `/docs/deployment/`
- Troubleshooting: `/docs/troubleshooting.md`

---

## 💡 Tips

- Start with **localhost** for development
- Use **LAN** for team collaboration
- Only use **production** when ready to deploy
- Always backup before updating
- Keep encryption keys safe!



