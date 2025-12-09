#!/bin/bash
# Backup ENCRYPTION_KEY from .env.production
# Run this BEFORE any major changes to ensure you can restore your data

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔐 TAV Engine - Encryption Key Backup Tool"
echo "=========================================="
echo ""

# Navigate to project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"

if [ ! -f ".env.production" ]; then
    echo -e "${RED}❌ .env.production not found${NC}"
    echo "This script must be run from the project root and .env.production must exist"
    exit 1
fi

# Extract ENCRYPTION_KEY
ENCRYPTION_KEY=$(grep "^ENCRYPTION_KEY=" .env.production | cut -d '=' -f2)

if [ -z "$ENCRYPTION_KEY" ]; then
    echo -e "${RED}❌ ENCRYPTION_KEY not found in .env.production${NC}"
    exit 1
fi

# Create secure backup directory
BACKUP_DIR="$PROJECT_ROOT/backups/keys"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"  # Owner only

# Create backup file with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/encryption_key_${TIMESTAMP}.txt"

cat > "$BACKUP_FILE" << EOF
# TAV Engine Encryption Key Backup
# Generated: $(date)
# ⚠️  KEEP THIS FILE SAFE AND SECRET!
# This key is required to decrypt all credentials in your database.

ENCRYPTION_KEY=$ENCRYPTION_KEY

# To restore, copy this ENCRYPTION_KEY value back into .env.production
EOF

chmod 600 "$BACKUP_FILE"  # Owner read/write only

echo -e "${GREEN}✅ Encryption key backed up to:${NC}"
echo "   $BACKUP_FILE"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT:${NC}"
echo "   - Store this file in a safe location (password manager, secure vault)"
echo "   - Never commit it to git"
echo "   - If you lose this key, encrypted credentials cannot be recovered"
echo ""
echo -e "${GREEN}📋 Recommended actions:${NC}"
echo "   1. Copy this key to your password manager"
echo "   2. Store backup file offline (USB drive, paper backup)"
echo "   3. Never change ENCRYPTION_KEY once credentials are created"
echo ""

# Also show current key (masked) for verification
MASKED_KEY="${ENCRYPTION_KEY:0:4}...${ENCRYPTION_KEY: -4}"
echo -e "${BLUE}🔑 Current key (masked):${NC} $MASKED_KEY"
echo ""
echo -e "${GREEN}✅ Backup complete!${NC}"

