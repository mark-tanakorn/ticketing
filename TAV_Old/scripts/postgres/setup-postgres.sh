#!/bin/bash
# Quick Start Script for PostgreSQL Setup
# Linux/Mac Shell Script

set -e

echo ""
echo "================================================"
echo "  PostgreSQL Setup for TAV Engine"
echo "================================================"
echo ""

# Check if Docker is running
if ! docker ps > /dev/null 2>&1; then
    echo "[ERROR] Docker is not running!"
    echo "Please start Docker and try again."
    exit 1
fi

echo "[1/4] Starting PostgreSQL and pgAdmin..."
docker-compose -f docker-compose.postgres.yml up -d

echo ""
echo "[2/4] Waiting for PostgreSQL to be ready..."
sleep 5

echo ""
echo "[3/4] Checking if .env file exists..."
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp env.postgres.example .env
    echo "[SUCCESS] Created .env file"
else
    echo "[INFO] .env file already exists"
    echo "[INFO] Make sure DATABASE_URL is set to PostgreSQL:"
    echo "       DATABASE_URL=postgresql://ticketing_user:ticketing_pass@localhost:5432/ticketing"
fi

echo ""
echo "[4/4] Installation complete!"
echo ""
echo "================================================"
echo "  PostgreSQL is running!"
echo "================================================"
echo ""
echo "  PostgreSQL:  localhost:5432"
echo "  Username:    ticketing_user"
echo "  Password:    ticketing_pass"
echo "  Database:    ticketing"
echo ""
echo "  pgAdmin:     http://localhost:5050"
echo "  Email:       admin@admin.com"
echo "  Password:    admin"
echo ""
echo "================================================"
echo "  Next Steps:"
echo "================================================"
echo ""
echo "  1. Check your .env file has:"
echo "     DATABASE_URL=postgresql://ticketing_user:ticketing_pass@localhost:5432/ticketing"
echo ""
echo "  2. Start your app:"
echo "     cd tav_opensource/scripts/native"
echo "     python start_native.py"
echo ""
echo "  3. Access pgAdmin at http://localhost:5050"
echo ""
echo "  To stop PostgreSQL:"
echo "     docker-compose -f docker-compose.postgres.yml down"
echo ""
echo "================================================"

