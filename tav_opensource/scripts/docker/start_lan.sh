#!/bin/bash
# TAV Engine - Quick Start (LAN Access)
# Share on your WiFi network
# Access: http://YOUR_IP:${FRONTEND_PORT:-3000}
#
# Port Configuration:
#   Create a .env file in the project root directory with:
#     BACKEND_PORT=5001
#     FRONTEND_PORT=3001
#     LAN_IP=192.168.1.100
#
#   Or pass as environment variables:
#     BACKEND_PORT=5001 ./start_lan.sh

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

echo "🌐 TAV Engine - Quick Start (LAN Access)"
echo "========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Show port configuration if non-default
if [ "$BACKEND_PORT" != "5000" ] || [ "$FRONTEND_PORT" != "3000" ]; then
    echo -e "${YELLOW}🔧 Custom Port Configuration:${NC}"
    echo "   Backend:  $BACKEND_PORT"
    echo "   Frontend: $FRONTEND_PORT"
    echo ""
fi

# Detect OS
OS="unknown"
case "$(uname -s)" in
    Linux*)     OS="Linux";;
    Darwin*)    OS="Mac";;
    CYGWIN*)    OS="Windows";;
    MINGW*)     OS="Windows";;
    MSYS*)      OS="Windows";;
esac

# Get local IP address
echo "🔍 Detecting your local IP address..."
if [ "$OS" = "Mac" ]; then
    LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n 1)
elif [ "$OS" = "Linux" ]; then
    LOCAL_IP=$(hostname -I | awk '{print $1}')
elif [ "$OS" = "Windows" ]; then
    LOCAL_IP=$(ipconfig | grep "IPv4" | grep -v "127.0.0.1" | awk '{print $NF}' | head -n 1 | tr -d '\r')
else
    echo -e "${RED}❌ Could not detect IP address. Please enter manually:${NC}"
    read -p "Enter your local IP (e.g. 192.168.1.100): " LOCAL_IP
fi

echo -e "${GREEN}✅ Local IP: $LOCAL_IP${NC}"
echo ""

# Ask about network shares
echo "🔍 Network Share Configuration (Optional)"
echo "=========================================="
echo "⚠️  IMPORTANT: Docker cannot mount UNC paths directly!"
echo ""
echo "To access network shares:"
echo "  1. First mount them as drive letters in Windows (run as Admin):"
echo "     net use Z: \\\\server\\share /user:username password /persistent:yes"
echo "  2. Then enter the drive letter path below (e.g., Z:\\folder)"
echo ""
echo "❌ DON'T use: \\\\server\\share\\path"
echo "✅ DO use:    Z:\\path (after mounting as Z:)"
echo ""
echo "You can mount up to 5 different network shares."
echo "They will be available inside Docker at: /mnt/share1, /mnt/share2, etc."
echo ""

# Clear any previously set NETWORK_SHARE variables
for i in {1..5}; do
    unset NETWORK_SHARE_${i}
done

# Array to store shares
declare -a SHARES

for i in {1..5}; do
    read -p "Share $i - Enter mounted drive path (e.g., Z:\\folder) or press Enter to skip: " SHARE_INPUT
    
    if [ -n "$SHARE_INPUT" ]; then
        # Preserve backslashes for Windows paths - escape them for docker-compose
        # Replace single backslash with double backslash to preserve in environment variable
        DOCKER_PATH=$(echo "$SHARE_INPUT" | sed 's/\\/\\\\/g')
        
        # Only export if path is not empty
        if [ -n "$DOCKER_PATH" ]; then
            # Use eval to properly set dynamic variable names
            eval "export NETWORK_SHARE_${i}='$DOCKER_PATH'"
            SHARES+=("Share $i: $SHARE_INPUT -> /mnt/share$i")
        fi
    fi
done

# Display configured shares
if [ ${#SHARES[@]} -gt 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Configured network shares:${NC}"
    for share in "${SHARES[@]}"; do
        echo "   $share"
    done
else
    echo -e "${YELLOW}⚠️  No network shares configured${NC}"
fi
echo ""

# Navigate to docker directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/../../deployment/docker"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running!${NC}"
    echo "Please start Docker Desktop and try again."
    exit 1
fi

# Export variables for docker-compose
export LAN_IP=$LOCAL_IP
export BACKEND_PORT
export FRONTEND_PORT

# Start services
echo "🔧 Building and starting containers..."
docker-compose -f docker-compose.lan.yml up -d --build

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check health
echo "🏥 Checking service health..."
docker-compose -f docker-compose.lan.yml ps

echo ""
echo "=========================================="
echo -e "${GREEN}✅ TAV Engine is running with LAN access!${NC}"
echo "=========================================="
echo ""
echo "📍 Local Access (this computer):"
echo "   Frontend: http://localhost:$FRONTEND_PORT"
echo "   Backend:  http://localhost:$BACKEND_PORT"
echo ""
echo "🌐 LAN Access (same WiFi network):"
echo -e "   ${BLUE}Frontend: http://${LOCAL_IP}:${FRONTEND_PORT}${NC}"
echo -e "   ${BLUE}Backend:  http://${LOCAL_IP}:${BACKEND_PORT}${NC}"
echo -e "   ${BLUE}API Docs: http://${LOCAL_IP}:${BACKEND_PORT}/docs${NC}"
echo ""
echo "📱 Share these URLs with others on your WiFi!"
echo ""
echo "📝 Useful Commands:"
echo "   View logs:    docker-compose -f docker-compose.lan.yml logs -f"
echo "   Stop:         docker-compose -f docker-compose.lan.yml down"
echo "   Restart:      docker-compose -f docker-compose.lan.yml restart"
echo ""
echo "🔒 Security: Dev mode enabled - anyone on WiFi can access"
echo ""

