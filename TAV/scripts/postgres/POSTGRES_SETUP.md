# PostgreSQL Setup for TAV Engine

This guide shows you how to set up PostgreSQL with Docker for your TAV Engine ticketing system.

## 🎯 Quick Start (3 Steps)

### Step 1: Start PostgreSQL

```bash
# Start PostgreSQL and pgAdmin
docker-compose -f docker-compose.postgres.yml up -d

# Check if it's running
docker-compose -f docker-compose.postgres.yml ps
```

### Step 2: Configure Your App

Copy the example environment file and update if needed:

```bash
# Copy the example file
cp env.postgres.example .env

# Or manually add to your existing .env file:
DATABASE_URL=postgresql://ticketing_user:ticketing_pass@localhost:5432/ticketing
```

### Step 3: Run Your App

**Option A: Native Python (Recommended for development)**

```bash
# The script will automatically use PostgreSQL from your .env
cd tav_opensource/scripts/native
python start_native.py
```

**Option B: Docker (Full containerized)**

Use the existing docker-compose files in `tav_opensource/deployment/docker/`

## 📊 What You Get

| Service | Access | Credentials |
|---------|--------|-------------|
| **PostgreSQL** | `localhost:5432` | User: `ticketing_user`<br>Password: `ticketing_pass`<br>Database: `ticketing` |
| **pgAdmin** | `http://localhost:5050` | Email: `admin@admin.com`<br>Password: `admin` |

## 🔧 PostgreSQL Configuration

### Default Settings

The Docker setup creates:
- **Database Name**: `ticketing`
- **Username**: `ticketing_user`
- **Password**: `ticketing_pass`
- **Port**: `5432`

### Custom Configuration

Edit `docker-compose.postgres.yml` to change:

```yaml
environment:
  POSTGRES_DB: your_database_name
  POSTGRES_USER: your_username
  POSTGRES_PASSWORD: your_secure_password
```

Then update your `.env` file:

```bash
DATABASE_URL=postgresql://your_username:your_secure_password@localhost:5432/your_database_name
```

## 🎨 Using pgAdmin

pgAdmin is a web-based database management tool.

### First Time Setup

1. Open http://localhost:5050
2. Login with `admin@admin.com` / `admin`
3. Right-click "Servers" → "Register" → "Server"
4. **General tab**: Name = `Ticketing DB`
5. **Connection tab**:
   - Host: `postgres-ticketing` (when pgAdmin is in Docker) OR `host.docker.internal` OR your local IP
   - Port: `5432`
   - Database: `ticketing`
   - Username: `ticketing_user`
   - Password: `ticketing_pass`
6. Click "Save"

### Common Tasks

- **View Tables**: Servers → Ticketing DB → Databases → ticketing → Schemas → public → Tables
- **Run Queries**: Right-click database → Query Tool
- **Export Data**: Right-click table → Import/Export

## 🛠️ Management Commands

### Start/Stop

```bash
# Start
docker-compose -f docker-compose.postgres.yml up -d

# Stop (keeps data)
docker-compose -f docker-compose.postgres.yml down

# Stop and remove data (⚠️ DESTROYS DATABASE)
docker-compose -f docker-compose.postgres.yml down -v
```

### View Logs

```bash
# All logs
docker-compose -f docker-compose.postgres.yml logs -f

# Just PostgreSQL
docker-compose -f docker-compose.postgres.yml logs -f postgres-ticketing

# Just pgAdmin
docker-compose -f docker-compose.postgres.yml logs -f pgadmin
```

### Database Backup

```bash
# Backup database to file
docker exec postgres-ticketing pg_dump -U ticketing_user ticketing > backup.sql

# Restore from backup
docker exec -i postgres-ticketing psql -U ticketing_user ticketing < backup.sql
```

### Access PostgreSQL CLI

```bash
# Connect to PostgreSQL shell
docker exec -it postgres-ticketing psql -U ticketing_user -d ticketing

# Common psql commands:
# \dt          - List tables
# \d+ users    - Describe users table
# \l           - List databases
# \q           - Quit
```

## 🔄 Migration from SQLite

If you're switching from SQLite to PostgreSQL:

### Option 1: Fresh Start (Recommended)

1. Start PostgreSQL (Step 1 above)
2. Update `.env` with PostgreSQL URL
3. Run the app - migrations will auto-create tables
4. Manually re-enter data or import

### Option 2: Migrate Data

```bash
# Install pgloader (Linux/Mac)
# Ubuntu: sudo apt-get install pgloader
# Mac: brew install pgloader

# Convert SQLite to PostgreSQL
pgloader \
  ./tav_opensource/backend/data/tav_engine.db \
  postgresql://ticketing_user:ticketing_pass@localhost:5432/ticketing
```

## 🐛 Troubleshooting

### Port 5432 Already in Use

```bash
# Find what's using port 5432
# Windows:
netstat -ano | findstr :5432

# Linux/Mac:
lsof -i :5432

# Change port in docker-compose.postgres.yml:
ports:
  - "5433:5432"  # Use 5433 instead

# Update .env:
DATABASE_URL=postgresql://ticketing_user:ticketing_pass@localhost:5433/ticketing
```

### Can't Connect from App

**If using Docker for backend**:
```bash
# Use service name instead of localhost
DATABASE_URL=postgresql://ticketing_user:ticketing_pass@postgres-ticketing:5432/ticketing
```

**If using native Python**:
```bash
# Use localhost
DATABASE_URL=postgresql://ticketing_user:ticketing_pass@localhost:5432/ticketing
```

### Database Connection Timeout

```bash
# Check if PostgreSQL is running
docker ps | grep postgres-ticketing

# Check PostgreSQL logs
docker logs postgres-ticketing

# Verify connection with psql
docker exec -it postgres-ticketing psql -U ticketing_user -d ticketing
```

### pgAdmin Can't Connect

When registering server in pgAdmin, try these hosts in order:
1. `postgres-ticketing` (if pgAdmin is in Docker)
2. `host.docker.internal` (Docker Desktop)
3. Your machine's IP address (e.g., `192.168.1.100`)

## 🔐 Security Notes

**⚠️ For Production:**

1. Change default passwords in `docker-compose.postgres.yml`
2. Use strong passwords in `.env`
3. Don't expose port 5432 to the internet
4. Use environment variables, not hardcoded credentials
5. Enable SSL for PostgreSQL connections
6. Restrict pgAdmin access or remove it

**Production Example:**

```yaml
# docker-compose.postgres.yml
environment:
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}  # From .env file
```

```bash
# .env (keep this file secret!)
POSTGRES_PASSWORD=your-very-secure-random-password-here
DATABASE_URL=postgresql://ticketing_user:${POSTGRES_PASSWORD}@localhost:5432/ticketing
```

## 📦 Data Persistence

Data is stored in Docker volumes:
- `ticketing_postgres_data` - Database files
- `ticketing_pgadmin_data` - pgAdmin settings

These persist even after stopping containers. To remove:

```bash
# ⚠️ WARNING: This deletes all data
docker volume rm ticketing_postgres_data ticketing_pgadmin_data
```

## 🚀 Performance Tips

### For Development
- Default settings are fine
- No special configuration needed

### For Production
Edit `docker-compose.postgres.yml`:

```yaml
postgres-ticketing:
  environment:
    # ... existing env vars ...
  command:
    - "postgres"
    - "-c"
    - "max_connections=200"
    - "-c"
    - "shared_buffers=256MB"
    - "-c"
    - "effective_cache_size=1GB"
    - "-c"
    - "work_mem=4MB"
```

Update your `.env`:

```bash
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100
```

## 📚 Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [pgAdmin Documentation](https://www.pgadmin.org/docs/)
- [Docker PostgreSQL Image](https://hub.docker.com/_/postgres)
- [SQLAlchemy PostgreSQL](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html)

## 🆘 Need Help?

Check the logs:
```bash
# PostgreSQL logs
docker logs postgres-ticketing

# Your app logs
cd tav_opensource/scripts/native
python start_native.py
```

Test connection:
```bash
# Test if PostgreSQL is accessible
docker exec -it postgres-ticketing pg_isready -U ticketing_user
```

