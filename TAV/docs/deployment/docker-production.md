# Docker Production Guide - 5-8 Minutes

Deploy TAV Engine to production with Docker, suitable for internet-exposed deployments.

## ⚡ Prerequisites

- **VPS or Server** (2GB RAM minimum, 4GB recommended)
- **Docker & Docker Compose** installed
- **Domain Name** (optional but recommended for SSL)
- **10 GB** free disk space

## 🚀 Quick Deployment

### Option 1: Automated Script (Recommended)

```bash
git clone https://github.com/Markepattsu/tav_opensource.git
cd tav_opensource
bash scripts/deployment/deploy_production.sh
```

The script will:
1. Check Docker installation
2. Generate secure keys
3. Create `.env.production` file
4. Build Docker images
5. Start all services
6. Perform health checks

### Option 2: Manual Deployment

Follow the manual steps below for more control.

## 📋 Manual Deployment Steps

### Step 1: Clone Repository

```bash
git clone https://github.com/yourorg/tav_opensource.git
cd tav_opensource
```

### Step 2: Create Production Configuration

```bash
cp deployment/configs/env.production.example .env
```

Edit `.env`:

```bash
# CRITICAL: Change these values!
SECRET_KEY=$(openssl rand -base64 32)
ENCRYPTION_KEY=$(openssl rand -base64 32 | cut -c1-32)

# Your domain
PUBLIC_URL=https://yourdomain.com
CORS_ORIGINS=["https://yourdomain.com"]
NEXT_PUBLIC_API_URL=https://yourdomain.com/api/v1

# IMPORTANT: Disable dev mode!
ENABLE_DEV_MODE=false

# Optional: AI API keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Step 3: Build and Start

```bash
cd deployment/docker
docker compose -f docker-compose.production.yml up -d
```

### Step 4: Verify Deployment

```bash
# Check container status
docker compose -f docker-compose.production.yml ps

# Check logs
docker compose -f docker-compose.production.yml logs -f

# Test health endpoint
curl http://localhost:5000/api/v1/health
```

## 🔒 SSL/HTTPS Setup (Recommended)

### Option 1: With Nginx (Built-in)

1. **Update DNS:** Point your domain to your server IP
   ```bash
   A record: yourdomain.com -> YOUR_SERVER_IP
   ```

2. **Start with Nginx profile:**
   ```bash
   docker compose -f docker-compose.production.yml --profile with-nginx up -d
   ```

3. **Install Certbot** (on host machine):
   ```bash
   # Ubuntu/Debian
   sudo apt install certbot python3-certbot-nginx

   # Generate certificate
   sudo certbot --nginx -d yourdomain.com
   ```

4. **Copy certificates to Docker:**
   ```bash
   sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem deployment/docker/nginx/ssl/cert.pem
   sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem deployment/docker/nginx/ssl/key.pem
   ```

5. **Update nginx.conf** (uncomment HTTPS section)

6. **Restart:**
   ```bash
   docker compose -f docker-compose.production.yml --profile with-nginx restart
   ```

### Option 2: External Reverse Proxy

Use Caddy, Traefik, or your existing reverse proxy. See [SSL Setup Guide](./ssl-setup.md).

## 🛠️ Management Commands

### View Logs
```bash
cd deployment/docker
docker compose -f docker-compose.production.yml logs -f
```

### Restart Services
```bash
docker compose -f docker-compose.production.yml restart
```

### Stop Services
```bash
docker compose -f docker-compose.production.yml down
```

### Update Deployment
```bash
# Pull latest code
git pull

# Rebuild and restart
docker compose -f docker-compose.production.yml up -d --build
```

### Scale Workers (if needed in future)
```bash
docker compose -f docker-compose.production.yml up -d --scale backend=2
```

## 💾 Backup Strategy

### Manual Backup

```bash
# Backup database
docker cp tav-backend-prod:/app/data/tav_engine.db ./backup_$(date +%Y%m%d).db

# Backup entire data volume
docker run --rm -v tav_production_backend_data:/data -v $(pwd):/backup alpine tar czf /backup/data_$(date +%Y%m%d).tar.gz -C /data .
```

### Automated Daily Backups

Create `/etc/cron.daily/tav-backup`:

```bash
#!/bin/bash
# TAV Engine automated backup

BACKUP_DIR="/backups/tav"
mkdir -p $BACKUP_DIR

# Backup database
docker cp tav-backend-prod:/app/data/tav_engine.db $BACKUP_DIR/tav_$(date +%Y%m%d).db

# Keep only last 7 days
find $BACKUP_DIR -name "tav_*.db" -mtime +7 -delete

# Optional: Upload to S3
# aws s3 cp $BACKUP_DIR/tav_$(date +%Y%m%d).db s3://your-backup-bucket/
```

Make executable:
```bash
chmod +x /etc/cron.daily/tav-backup
```

### Restore from Backup

```bash
# Stop containers
docker compose -f docker-compose.production.yml down

# Restore database
docker cp backup_20251112.db tav-backend-prod:/app/data/tav_engine.db

# Start containers
docker compose -f docker-compose.production.yml up -d
```

## 🔍 Monitoring

### Health Checks

```bash
# Backend health
curl https://yourdomain.com/api/v1/health

# Expected response: {"status": "healthy"}
```

### Container Status

```bash
# Check if containers are running
docker ps

# Check container health
docker inspect tav-backend-prod | grep Health -A 10
```

### Resource Usage

```bash
# Real-time stats
docker stats

# Disk usage
docker system df
```

### Log Monitoring

```bash
# Follow logs
docker compose -f docker-compose.production.yml logs -f --tail=100

# Search logs
docker compose -f docker-compose.production.yml logs | grep ERROR
```

## 🔐 Security Best Practices

### 1. Environment Variables
- ✅ Never commit `.env.production` to git
- ✅ Use strong random keys (32+ characters)
- ✅ Rotate keys periodically

### 2. Firewall Configuration

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 22     # SSH
sudo ufw allow 80     # HTTP
sudo ufw allow 443    # HTTPS
sudo ufw enable

# Close unused ports
sudo ufw deny 5000    # Don't expose backend directly
sudo ufw deny 3000    # Don't expose frontend directly
```

### 3. Docker Security

```bash
# Run containers as non-root (already configured)
# Enable Docker content trust
export DOCKER_CONTENT_TRUST=1

# Regular updates
docker compose -f docker-compose.production.yml pull
docker compose -f docker-compose.production.yml up -d
```

### 4. Application Security

- ✅ Set `ENABLE_DEV_MODE=false`
- ✅ Configure CORS for your domain only
- ✅ Enable rate limiting
- ✅ Use HTTPS/SSL
- ✅ Regular backups

## 📊 Performance Tuning

### Resource Limits

Edit `docker-compose.production.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          memory: 512M
```

### Backend Workers

Increase workers for better concurrency:

```yaml
services:
  backend:
    command: >
      sh -c "
      alembic upgrade head &&
      uvicorn app.main:app --host 0.0.0.0 --port 5000 --workers 4
      "
```

Rule of thumb: `workers = (2 x CPU cores) + 1`

### Database Optimization

SQLite is suitable for:
- ✅ Up to 100-500 workflows
- ✅ Up to 1000 executions/day
- ✅ Single server deployments

For higher load, PostgreSQL will be supported in v1.1+.

## 🔄 Zero-Downtime Updates

```bash
# Build new images
docker compose -f docker-compose.production.yml build

# Update services one by one
docker compose -f docker-compose.production.yml up -d --no-deps backend
# Wait for health check
sleep 10
docker compose -f docker-compose.production.yml up -d --no-deps frontend
```

## 🌐 Webhook Configuration

With production deployment, webhooks work out of the box:

1. **Create workflow** with webhook trigger
2. **Copy webhook URL** (format: `https://yourdomain.com/api/v1/webhook/{workflow_id}/{token}`)
3. **Configure external service** to send webhooks to this URL
4. **Test webhook** with curl:
   ```bash
   curl -X POST https://yourdomain.com/api/v1/webhook/YOUR_WORKFLOW_ID/YOUR_TOKEN \
     -H "Content-Type: application/json" \
     -d '{"test": "data"}'
   ```

## 🔍 Troubleshooting

### Container Keeps Restarting

```bash
# Check logs
docker logs tav-backend-prod --tail=50

# Common issues:
# - Database migration failed
# - Invalid environment variables
# - Port already in use
```

### Database Locked

```bash
# Stop containers
docker compose -f docker-compose.production.yml down

# Remove lock files
docker volume inspect tav_production_backend_data
# Note the Mountpoint, then:
sudo rm /var/lib/docker/volumes/tav_production_backend_data/_data/*.lock

# Restart
docker compose -f docker-compose.production.yml up -d
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Reduce worker count or increase server RAM
```

### SSL Certificate Issues

```bash
# Renew certificate
sudo certbot renew

# Test renewal
sudo certbot renew --dry-run

# Auto-renewal is enabled by default
```

## 📈 Scaling Checklist

When you outgrow SQLite:
- [ ] Move to PostgreSQL (v1.1+)
- [ ] Add Redis for caching
- [ ] Use external file storage (S3)
- [ ] Add load balancer
- [ ] Separate database server
- [ ] Add monitoring (Grafana, Prometheus)

## 💡 Tips

1. **First deployment** may take 3-5 minutes (Docker image builds)
2. **Subsequent updates** take 30-60 seconds
3. **Always backup** before updates
4. **Monitor logs** for first 24 hours after deployment
5. **Test workflows** after deployment

## 🎯 Next Steps

- [Configure SSL/HTTPS](./ssl-setup.md)
- [Set up monitoring](#)
- [Configure backups](#)
- [Create your first workflow](#)

---

**Need help?** Check [Troubleshooting](./troubleshooting.md) or ask on [Discord](https://discord.gg/your-server).

