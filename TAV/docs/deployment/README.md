# TAV Engine Deployment Guide

Welcome to TAV Engine deployment! Choose the method that best fits your needs.

## 🚀 Deployment Options

### 1. Quick Start (2 minutes) - No Docker Required
**Best for:** Testing, development, demos

- ✅ Fastest way to get started
- ✅ No Docker needed
- ✅ Uses SQLite (zero config)
- ❌ No isolation
- ❌ Manual startup required

[👉 Go to Quick Start Guide](./quick-start.md)

---

### 2. Docker Local (3 minutes) - Development
**Best for:** Isolated development, testing

- ✅ Container isolation
- ✅ Auto-restarts
- ✅ Uses SQLite (simple)
- ✅ Easy to reset
- ❌ Requires Docker

[👉 Go to Docker Local Guide](./docker-local.md)

---

### 3. Docker Production (5-8 minutes) - Production Ready
**Best for:** Real deployments, internet-exposed applications

- ✅ Production-optimized
- ✅ Persistent data volumes
- ✅ Health checks
- ✅ SSL-ready
- ✅ Auto-restart on failure
- ❌ More setup required

[👉 Go to Docker Production Guide](./docker-production.md)

---

## 📊 Comparison Table

| Feature | Quick Start | Docker Local | Docker Production |
|---------|-------------|--------------|-------------------|
| **Setup Time** | 2 min | 3 min | 5-8 min |
| **Requires Docker** | ❌ | ✅ | ✅ |
| **Database** | SQLite | SQLite | SQLite |
| **Isolation** | ❌ | ✅ | ✅ |
| **Auto-restart** | ❌ | ✅ | ✅ |
| **SSL/HTTPS** | ❌ | ❌ | ✅ (optional) |
| **Production Ready** | ❌ | ❌ | ✅ |
| **Internet Exposed** | Manual | Manual | ✅ |
| **Webhooks** | ⚠️ (tunnel) | ⚠️ (tunnel) | ✅ |

---

## 🗄️ Database: SQLite

All deployment methods currently use **SQLite**, which is suitable for:
- ✅ Low to medium traffic (up to 100-500 workflows)
- ✅ Single-server deployments
- ✅ Up to 1000 concurrent executions per day
- ✅ Easy backups (single file)
- ✅ Zero configuration

**Note:** PostgreSQL support is planned for high-traffic deployments in v1.1+

---

## 📖 Additional Guides

- [SSL/HTTPS Setup](./ssl-setup.md) - Configure HTTPS with Let's Encrypt
- [Troubleshooting](./troubleshooting.md) - Common issues and solutions
- [Migration Guide](./migration-guide.md) - Upgrading or migrating data

---

## 🔒 Security Checklist (Production Only)

Before deploying to production:

- [ ] Set `ENABLE_DEV_MODE=false` in `.env.production`
- [ ] Generate new `SECRET_KEY` and `ENCRYPTION_KEY`
- [ ] Configure `CORS_ORIGINS` for your domain
- [ ] Enable HTTPS/SSL
- [ ] Set up regular database backups
- [ ] Configure firewall rules
- [ ] Review rate limiting settings

---

## 💾 Backup & Restore

### Quick Backup
```bash
# Native / Docker Local
cp backend/data/tav_engine.db backup_$(date +%Y%m%d).db

# Docker Production
docker cp tav-backend-prod:/app/data/tav_engine.db ./backup_$(date +%Y%m%d).db
```

### Automated Backups (recommended for production)
```bash
# Add to crontab: daily at 2 AM
0 2 * * * docker cp tav-backend-prod:/app/data/tav_engine.db /backups/tav_$(date +\%Y\%m\%d).db
```

---

## 🆘 Need Help?

- **Documentation:** Browse other guides in this folder
- **Issues:** [GitHub Issues](https://github.com/yourorg/tav_opensource/issues)
- **Community:** [Discord Server](https://discord.gg/your-server)

---

## 🎯 Next Steps

1. Choose your deployment method above
2. Follow the step-by-step guide
3. Access your TAV Engine instance
4. Start creating workflows!

