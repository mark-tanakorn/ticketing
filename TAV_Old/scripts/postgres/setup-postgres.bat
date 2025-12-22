@echo off
REM Quick Start Script for PostgreSQL Setup
REM Windows Batch Script

echo.
echo ================================================
echo   PostgreSQL Setup for TAV Engine
echo ================================================
echo.

REM Check if Docker is running
docker ps >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo [1/4] Starting PostgreSQL and pgAdmin...
docker-compose -f docker-compose.postgres.yml up -d

if errorlevel 1 (
    echo [ERROR] Failed to start PostgreSQL!
    pause
    exit /b 1
)

echo.
echo [2/4] Waiting for PostgreSQL to be ready...
timeout /t 5 /nobreak >nul

echo.
echo [3/4] Checking if .env file exists...
if not exist .env (
    echo Creating .env file from template...
    copy env.postgres.example .env
    echo [SUCCESS] Created .env file
) else (
    echo [INFO] .env file already exists
    echo [INFO] Make sure DATABASE_URL is set to PostgreSQL:
    echo        DATABASE_URL=postgresql://ticketing_user:ticketing_pass@localhost:5432/ticketing
)

echo.
echo [4/4] Installation complete!
echo.
echo ================================================
echo   PostgreSQL is running!
echo ================================================
echo.
echo   PostgreSQL:  localhost:5432
echo   Username:    ticketing_user
echo   Password:    ticketing_pass
echo   Database:    ticketing
echo.
echo   pgAdmin:     http://localhost:5050
echo   Email:       admin@admin.com
echo   Password:    admin
echo.
echo ================================================
echo   Next Steps:
echo ================================================
echo.
echo   1. Check your .env file has:
echo      DATABASE_URL=postgresql://ticketing_user:ticketing_pass@localhost:5432/ticketing
echo.
echo   2. Start your app:
echo      cd tav_opensource\scripts\native
echo      python start_native.py
echo.
echo   3. Access pgAdmin at http://localhost:5050
echo.
echo   To stop PostgreSQL:
echo      docker-compose -f docker-compose.postgres.yml down
echo.
echo ================================================

pause

