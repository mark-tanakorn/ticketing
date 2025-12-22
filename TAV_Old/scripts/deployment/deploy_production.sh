#!/bin/bash
# TAV Engine - Production Deployment Script
# Deploys TAV Engine with SQLite for production use

set -e

echo "🚀 TAV Engine - Production Deployment"
echo "======================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "Please install Docker from https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not available${NC}"
    echo "Please install Docker Compose v2"
    exit 1
fi

echo -e "${GREEN}✅ Docker and Docker Compose are installed${NC}"
echo ""

# Navigate to project root (script is in deployment/scripts/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/../.."
cd "$PROJECT_ROOT"

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo "⚙️  Creating production configuration..."
    
    # Generate random secrets ONCE (never regenerate)
    SECRET_KEY=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
    ENCRYPTION_KEY=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
    
    cat > .env.production << EOF
# TAV Engine Production Configuration
# Generated: $(date)
# ⚠️  WARNING: DO NOT DELETE THIS FILE!
# ⚠️  Changing ENCRYPTION_KEY will make all encrypted data (credentials) unreadable!

# Environment
ENVIRONMENT=production

# Security Keys (KEEP THESE SECRET AND NEVER CHANGE ENCRYPTION_KEY!)
SECRET_KEY=$SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY

# Public URL (change to your domain)
PUBLIC_URL=http://localhost:3000

# Authentication (IMPORTANT: Set to false for production)
ENABLE_DEV_MODE=false

# CORS Origins (adjust for your domain)
CORS_ORIGINS=["http://localhost:3000","http://localhost:5000"]

# API URL for frontend
NEXT_PUBLIC_API_URL=http://localhost:5000/api/v1

# Ports
BACKEND_PORT=5000
FRONTEND_PORT=3000
HTTP_PORT=80
HTTPS_PORT=443

# Logging
LOG_LEVEL=INFO

# AI API Keys (optional - add your keys here)
# OPENAI_API_KEY=
# ANTHROPIC_API_KEY=
# DEEPSEEK_API_KEY=
# GOOGLE_API_KEY=
EOF
    
    echo -e "${GREEN}✅ Created .env.production${NC}"
    echo ""
    echo -e "${RED}⚠️  CRITICAL: Keep .env.production safe!${NC}"
    echo -e "${RED}   - Never delete or lose this file${NC}"
    echo -e "${RED}   - Never change ENCRYPTION_KEY (it protects your credentials)${NC}"
    echo -e "${RED}   - Add it to .gitignore (already done)${NC}"
    echo ""
    echo -e "${YELLOW}📋 TODO: Edit .env.production and set:${NC}"
    echo "   - PUBLIC_URL (your domain)"
    echo "   - ENABLE_DEV_MODE=false (for production)"
    echo "   - CORS_ORIGINS (your domain)"
    echo ""
    read -p "Press Enter to continue after reviewing .env.production..."
else
    echo -e "${GREEN}✅ Found existing .env.production (keeping encryption keys)${NC}"
    echo ""
fi

# Load environment variables
export $(cat .env.production | grep -v '^#' | xargs)

echo "🐳 Building Docker images..."
docker compose -f deployment/docker/docker-compose.production.yml build

echo ""
echo "🚀 Starting services..."
docker compose -f deployment/docker/docker-compose.production.yml up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check backend health
echo "Checking backend..."
for i in {1..15}; do
    if docker exec tav-backend-prod curl -s http://localhost:5000/api/v1/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is healthy${NC}"
        break
    fi
    if [ $i -eq 15 ]; then
        echo -e "${RED}❌ Backend health check failed${NC}"
        echo "Check logs: docker compose -f docker-compose.production.yml logs backend"
        exit 1
    fi
    sleep 2
done

echo ""
echo "============================================"
echo -e "${GREEN}✅ TAV Engine is deployed!${NC}"
echo "============================================"
echo ""
echo "📍 Access your instance:"
echo "   Frontend: http://localhost:${FRONTEND_PORT:-3000}"
echo "   Backend:  http://localhost:${BACKEND_PORT:-5000}"
echo "   API Docs: http://localhost:${BACKEND_PORT:-5000}/docs"
echo ""
echo "📊 Management commands:"
echo "   View logs:    docker compose -f deployment/docker/docker-compose.production.yml logs -f"
echo "   Stop:         docker compose -f deployment/docker/docker-compose.production.yml down"
echo "   Restart:      docker compose -f deployment/docker/docker-compose.production.yml restart"
echo "   Update:       git pull && docker compose -f deployment/docker/docker-compose.production.yml up -d --build"
echo ""
echo "💾 Database backup:"
echo "   docker cp tav-backend-prod:/app/data/tav_engine.db ./backup_\$(date +%Y%m%d).db"
echo ""
echo "💡 Notes:"
echo "   - Using SQLite (suitable for low-medium traffic)"
echo "   - Database is persisted in Docker volume 'backend_data'"
echo "   - For SSL/HTTPS, see docs/deployment/docker-production.md"
echo "   - For high traffic, consider PostgreSQL (future update)"
echo ""
echo -e "${BLUE}🎉 Deployment complete!${NC}"

