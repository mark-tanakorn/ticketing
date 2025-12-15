#!/bin/bash
# TAV Engine - Production Start
# For internet-accessible deployments with SSL

set -e

echo "🚀 TAV Engine - Production Deployment"
echo "======================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Navigate to docker directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/../../deployment/docker"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo ""
    echo "Please create .env file with:"
    echo "  1. Copy template: cp ../configs/env.production.example .env"
    echo "  2. Edit with your values: nano .env"
    echo "  3. Set DOMAIN, SECRET_KEY, ENCRYPTION_KEY"
    echo ""
    exit 1
fi

# Check required variables
echo "🔍 Checking required environment variables..."
source .env

if [ -z "$DOMAIN" ] || [ -z "$SECRET_KEY" ] || [ -z "$ENCRYPTION_KEY" ]; then
    echo -e "${RED}❌ Missing required variables in .env${NC}"
    echo ""
    echo "Required variables:"
    echo "  - DOMAIN (your domain name)"
    echo "  - SECRET_KEY (generate with: openssl rand -base64 32)"
    echo "  - ENCRYPTION_KEY (generate with: openssl rand -base64 32)"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ Environment variables OK${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running!${NC}"
    echo "Please start Docker Desktop and try again."
    exit 1
fi

# Start services
echo "🔧 Building and starting containers..."
docker-compose -f docker-compose.production.yml up -d --build

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 15

# Check health
echo "🏥 Checking service health..."
docker-compose -f docker-compose.production.yml ps

echo ""
echo "=========================================="
echo -e "${GREEN}✅ TAV Engine is running in production mode!${NC}"
echo "=========================================="
echo ""
echo "📍 Access Points:"
echo "   Frontend: https://${DOMAIN}"
echo "   Backend:  https://${DOMAIN}/api"
echo "   API Docs: https://${DOMAIN}/api/docs"
echo ""
echo "⚠️  Important Next Steps:"
echo "   1. Set up SSL certificate (Let's Encrypt recommended)"
echo "   2. Configure nginx reverse proxy"
echo "   3. Set up firewall rules"
echo "   4. Configure domain DNS"
echo ""
echo "📝 Useful Commands:"
echo "   View logs:    docker-compose -f docker-compose.production.yml logs -f"
echo "   Stop:         docker-compose -f docker-compose.production.yml down"
echo "   Restart:      docker-compose -f docker-compose.production.yml restart"
echo ""
echo "🔒 Security: Dev mode disabled, authentication enabled"
echo ""

