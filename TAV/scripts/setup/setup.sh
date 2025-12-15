#!/bin/bash
# TAV Opensource - Development Setup Script
# Automatically sets up your development environment

set -e  # Exit on error

echo "🚀 TAV Opensource - Development Setup"
echo "======================================"
echo ""

# Check Python version
echo "🐍 Checking Python..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "   Found Python $python_version"

# Check Node version
echo "📦 Checking Node.js..."
node_version=$(node --version)
echo "   Found Node $node_version"

# Backend setup
echo ""
echo "🔧 Setting up Backend..."
cd backend
if [ ! -d "venv" ]; then
    echo "   Creating virtual environment..."
    python -m venv venv
fi

echo "   Activating virtual environment..."
source venv/bin/activate

echo "   Installing Python dependencies..."
pip install -r requirements.txt --quiet

echo "   ✅ Backend setup complete"

# Frontend setup
cd ../ui
echo ""
echo "🎨 Setting up Frontend..."
echo "   Installing Node dependencies..."
npm install --silent

echo "   ✅ Frontend setup complete"

# Run initial tests
cd ../..
echo ""
echo "🧪 Running test verification..."
echo "   Backend tests..."
cd backend
python -m pytest tests/unit -q --tb=no | tail -n 3

cd ../ui
echo "   Frontend tests..."
npm test -- --passWithNoTests 2>&1 | grep "Test Suites"

cd ..
echo ""
echo "======================================"
echo "✅ Setup Complete!"
echo ""
echo "📝 Next steps:"
echo "   Unified dev:  python scripts/dev/start_dev.py"
echo "   Backend dev:  cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "   Frontend dev: cd ui && npm run dev"
echo "   Run tests:    python scripts/test/test_all.py"
echo "   Docker:       make docker-up"
echo "   Quick help:   make help"
echo ""
echo "🎉 Happy coding!"

