#!/bin/bash
# Docker Rebuild Script - Fixes dependency/cache issues

echo "🐳 TAV Docker - Clean Rebuild"
echo "=============================="
echo ""

# Navigate to docker directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/../../deployment/docker"

echo "🛑 Stopping all containers..."
docker-compose down

echo "🧹 Removing old images..."
docker-compose rm -f

echo "🔨 Rebuilding without cache..."
docker-compose build --no-cache

echo "🚀 Starting fresh containers..."
docker-compose up -d

echo ""
echo "✅ Rebuild complete!"
echo ""
echo "📊 Status:"
docker-compose ps

echo ""
echo "📝 Logs:"
echo "   View all:      docker-compose logs -f"
echo "   Backend only:  docker-compose logs -f backend"
echo "   Frontend only: docker-compose logs -f frontend"
echo ""
echo "🌐 Access:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:5000"

