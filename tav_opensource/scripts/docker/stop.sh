#!/bin/bash
# TAV Engine - Stop Script
# Stops backend and frontend services started by quick-start.sh

set -e

echo "🛑 Stopping TAV Engine..."
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Navigate to project root (script is in deployment/scripts/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/../.."
cd "$PROJECT_ROOT"

# Stop backend
if [ -f "backend/.backend.pid" ]; then
    BACKEND_PID=$(cat backend/.backend.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo "Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        echo -e "${GREEN}✅ Backend stopped${NC}"
    else
        echo -e "${YELLOW}⚠️  Backend process not found${NC}"
    fi
    rm backend/.backend.pid
else
    echo -e "${YELLOW}⚠️  No backend PID file found${NC}"
fi

# Stop frontend
if [ -f "ui/.frontend.pid" ]; then
    FRONTEND_PID=$(cat ui/.frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo "Stopping frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID
        echo -e "${GREEN}✅ Frontend stopped${NC}"
    else
        echo -e "${YELLOW}⚠️  Frontend process not found${NC}"
    fi
    rm ui/.frontend.pid
else
    echo -e "${YELLOW}⚠️  No frontend PID file found${NC}"
fi

# Clean up any remaining node/python processes (optional, commented out for safety)
# pkill -f "uvicorn app.main:app" 2>/dev/null || true
# pkill -f "next dev" 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ TAV Engine stopped${NC}"

