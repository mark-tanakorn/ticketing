# TAV Opensource - Development Setup Script (Windows)
# Automatically sets up your development environment

Write-Host "🚀 TAV Opensource - Development Setup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "🐍 Checking Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
Write-Host "   Found $pythonVersion" -ForegroundColor Green

# Check Node version
Write-Host "📦 Checking Node.js..." -ForegroundColor Yellow
$nodeVersion = node --version
Write-Host "   Found Node $nodeVersion" -ForegroundColor Green

# Backend setup
Write-Host ""
Write-Host "🔧 Setting up Backend..." -ForegroundColor Yellow
Set-Location backend

if (-not (Test-Path "venv")) {
    Write-Host "   Creating virtual environment..." -ForegroundColor Gray
    python -m venv venv
}

Write-Host "   Activating virtual environment..." -ForegroundColor Gray
.\venv\Scripts\Activate.ps1

Write-Host "   Installing Python dependencies..." -ForegroundColor Gray
pip install -r requirements.txt --quiet

Write-Host "   ✅ Backend setup complete" -ForegroundColor Green

# Frontend setup
Set-Location ../ui
Write-Host ""
Write-Host "🎨 Setting up Frontend..." -ForegroundColor Yellow
Write-Host "   Installing Node dependencies..." -ForegroundColor Gray
npm install --silent

Write-Host "   ✅ Frontend setup complete" -ForegroundColor Green

# Run initial tests
Set-Location ..
Write-Host ""
Write-Host "🧪 Running test verification..." -ForegroundColor Yellow
Write-Host "   Backend tests..." -ForegroundColor Gray
Set-Location backend
python -m pytest tests/unit -q --tb=no 2>&1 | Select-Object -Last 3

Set-Location ../ui
Write-Host "   Frontend tests..." -ForegroundColor Gray
npm test 2>&1 | Select-String "Test Suites"

Set-Location ../..
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Yellow
Write-Host "   Unified dev:  python scripts\dev\start_dev.py"
Write-Host "   Backend dev:  cd backend && .\venv\Scripts\Activate.ps1 && uvicorn app.main:app --reload"
Write-Host "   Frontend dev: cd ui && npm run dev"
Write-Host "   Run tests:    python scripts\test\test_all.py"
Write-Host "   Docker:       make docker-up"
Write-Host "   Quick help:   make help"
Write-Host ""
Write-Host "🎉 Happy coding!" -ForegroundColor Cyan

