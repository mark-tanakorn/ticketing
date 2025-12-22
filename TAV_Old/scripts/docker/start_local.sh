#!/bin/bash
# TAV Engine - Quick Start (Localhost)
# Fastest setup for solo development
# Access: http://localhost:${FRONTEND_PORT:-3000}
#
# Port Configuration:
#   Create a .env file in the project root directory with:
#     BACKEND_PORT=5001
#     FRONTEND_PORT=3001
#
#   Or pass as environment variables:
#     BACKEND_PORT=5001 ./start_local.sh

set -e

# Get project root directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/../.."

# Load .env from project root if it exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "📄 Loading configuration from .env file..."
    set -a  # automatically export all variables
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Default ports (env vars take precedence over .env)
BACKEND_PORT=${BACKEND_PORT:-5000}
FRONTEND_PORT=${FRONTEND_PORT:-3000}

echo "🚀 TAV Engine - Quick Start (Localhost)"
echo "========================================"
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Show port configuration if non-default
if [ "$BACKEND_PORT" != "5000" ] || [ "$FRONTEND_PORT" != "3000" ]; then
    echo -e "${YELLOW}🔧 Custom Port Configuration:${NC}"
    echo "   Backend:  $BACKEND_PORT"
    echo "   Frontend: $FRONTEND_PORT"
    echo ""
fi

# Navigate to docker directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/../../deployment/docker"

echo -e "${BLUE}📦 Starting TAV Engine with Docker...${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running!${NC}"
    echo "Please start Docker Desktop and try again."
    exit 1
fi

# Export ports for docker-compose
export BACKEND_PORT
export FRONTEND_PORT

# Start services
echo "🔧 Building and starting containers..."
docker-compose up -d --build

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check health
echo "🏥 Checking service health..."
docker-compose ps

echo ""
echo "=========================================="
echo -e "${GREEN}✅ TAV Engine is running!${NC}"
echo "=========================================="
echo ""
echo "📍 Access Points:"
echo "   Frontend: http://localhost:$FRONTEND_PORT"
echo "   Backend:  http://localhost:$BACKEND_PORT"
echo "   API Docs: http://localhost:$BACKEND_PORT/docs"
echo ""
echo "📊 Tech Stack:"
echo "   - Backend: FastAPI + SQLite"
echo "   - Frontend: Next.js"
echo "   - Dev Mode: Enabled (no auth required)"
echo ""
echo "📝 Useful Commands:"
echo "   View logs:    docker-compose logs -f"
echo "   Stop:         docker-compose down"
echo "   Restart:      docker-compose restart"
echo "   Rebuild:      docker-compose up -d --build"
echo ""
echo "🔍 Troubleshooting:"
echo "   - Check logs: docker-compose logs backend frontend"
echo "   - Reset data: docker-compose down -v && docker-compose up -d"
echo ""

