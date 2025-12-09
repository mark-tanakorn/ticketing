# Scripts Directory

All project scripts organized by purpose.

## 📁 Directory Structure

```
scripts/
├── setup/              # Initial setup and installation
│   ├── setup.sh        # Setup for Linux/Mac
│   └── setup.ps1       # Setup for Windows
├── dev/                # Development tools
│   ├── start_dev.py    # Unified dev server (backend + frontend)
│   └── start_dev.bat   # Windows wrapper for start_dev.py
├── docker/             # Docker management
│   ├── start_local.sh  # Start local Docker environment
│   ├── start_lan.sh    # Start LAN-accessible Docker
│   ├── start_production.sh  # Start production Docker
│   ├── stop.sh         # Stop all Docker containers
│   └── rebuild.sh      # Rebuild Docker images (clean)
├── deployment/         # Production deployment
│   └── deploy_production.sh  # Production deployment script
├── test/               # Testing utilities
│   └── test_all.py     # Comprehensive test runner
└── hooks/              # Git hooks
    └── pre-commit      # Pre-commit quality checks
```

## 🚀 Quick Commands

### Setup (First Time)
```bash
# Linux/Mac
bash scripts/setup/setup.sh

# Windows
.\scripts\setup\setup.ps1

# Or use Make
make setup
```

### Development
```bash
# Start unified dev server (recommended)
python scripts/dev/start_dev.py
# or
make start-dev

# Start individual servers
make dev-backend   # Backend only
make dev-frontend  # Frontend only
```

### Docker
```bash
# Local development
make docker-up
# or
bash scripts/docker/start_local.sh

# LAN-accessible (test on other devices)
make docker-lan

# Production mode
make docker-prod

# Stop all
make docker-stop

# Clean rebuild (fixes cache issues)
make docker-rebuild
```

### Testing
```bash
# Run all tests (backend + frontend)
make test

# Comprehensive test suite with coverage
make test-all
# or
python scripts/test/test_all.py
```

### Deployment
```bash
# Deploy to production
make deploy-prod
# or
bash scripts/deployment/deploy_production.sh
```

## 📝 Notes

- All scripts are designed to be run from the **project root directory**
- Use `make help` to see all available Makefile commands
- Windows users: Use PowerShell for `.ps1` scripts, Git Bash for `.sh` scripts
- For git hooks: Run `make install-hooks` to enable pre-commit checks

