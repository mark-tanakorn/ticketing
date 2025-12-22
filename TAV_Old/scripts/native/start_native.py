#!/usr/bin/env python3
"""
TAV Engine - Native Windows Startup Script (LAN-enabled)
Runs both frontend and backend without Docker
Perfect for network share access!
Auto-detects IP for LAN access

Port Configuration:
    Create a .env file in the project root directory with:
        BACKEND_PORT=5001
        FRONTEND_PORT=3001
    
    Or use command-line arguments (takes precedence):
        python start_native.py --backend-port 5001
        python start_native.py -b 5001 -f 3001
"""

import os
import sys
import subprocess
import signal
import time
import socket
import argparse
from pathlib import Path

# Default ports
DEFAULT_BACKEND_PORT = 5000
DEFAULT_FRONTEND_PORT = 3000


def load_env_file(project_root):
    """Load .env file from project root if it exists."""
    env_file = project_root / ".env"
    if env_file.exists():
        print_colored("📄 Loading configuration from .env file...", Colors.BLUE)
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    # Parse KEY=VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        # Only set if not already in environment (CLI/env takes precedence)
                        if key not in os.environ:
                            os.environ[key] = value
            return True
        except Exception as e:
            print_colored(f"⚠️  Could not read .env file: {e}", Colors.YELLOW)
    return False

# Color codes for Windows
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_colored(text, color):
    print(f"{color}{text}{Colors.RESET}")

def print_banner():
    print_colored("=" * 60, Colors.BLUE)
    print_colored("🚀 TAV Engine - Native Windows Startup", Colors.GREEN)
    print_colored("=" * 60, Colors.BLUE)
    print()

def check_dependencies():
    """Check if Python and Node.js are available"""
    print_colored("🔍 Checking dependencies...", Colors.BLUE)
    
    # Check Python
    try:
        python_version = sys.version.split()[0]
        print_colored(f"✅ Python {python_version}", Colors.GREEN)
    except:
        print_colored("❌ Python not found!", Colors.RED)
        return False
    
    # Check Node.js (use npm.cmd on Windows)
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    try:
        result = subprocess.run([npm_cmd, '--version'], capture_output=True, text=True)
        npm_version = result.stdout.strip()
        print_colored(f"✅ npm {npm_version}", Colors.GREEN)
    except:
        print_colored("❌ npm not found! Please install Node.js", Colors.RED)
        return False
    
    print()
    return True, npm_cmd

def get_local_ip():
    """Auto-detect the local IP address"""
    try:
        # Create a socket to get the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

def get_project_root():
    """Get the project root directory"""
    script_path = Path(__file__).resolve()
    return script_path.parent.parent.parent

def create_minimal_env_files(project_root):
    """
    Create minimal .env files with only static settings.
    Dynamic settings (CORS, BASE_URL, etc.) are handled at runtime.
    """
    backend_dir = project_root / "backend"
    backend_env = backend_dir / ".env"
    
    # Create backend .env with ONLY static settings
    env_content = """# TAV Engine - Static Configuration
# Dynamic settings (CORS, BASE_URL) are handled at runtime

# Database
DATABASE_URL=sqlite:///./data/tav_engine.db

# Development mode
ENABLE_DEV_MODE=true
ENVIRONMENT=development
LOG_LEVEL=INFO

# Security keys (change in production!)
SECRET_KEY=dev-secret-key-change-in-production-min-32-chars
ENCRYPTION_KEY=dev-encryption-key-change-prod-32b

# Project info
PROJECT_NAME=TAV Engine
VERSION=1.0.0

# NOTE: CORS_ORIGINS and BASE_URL are NOT set here
# They are dynamically configured based on how you access the app:
# - localhost → uses localhost URLs
# - LAN IP → uses LAN IP URLs
"""
    
    try:
        with open(backend_env, 'w') as f:
            f.write(env_content)
        print_colored(f"✅ Created minimal .env in backend (static settings only)", Colors.GREEN)
    except Exception as e:
        print_colored(f"⚠️  Could not create .env file: {e}", Colors.YELLOW)
    
    # Delete frontend .env.local if it exists (force dynamic detection)
    frontend_dir = project_root / "ui"
    frontend_env_local = frontend_dir / ".env.local"
    if frontend_env_local.exists():
        try:
            frontend_env_local.unlink()
            print_colored(f"✅ Removed frontend .env.local (using dynamic detection)", Colors.GREEN)
        except Exception as e:
            print_colored(f"⚠️  Could not remove .env.local: {e}", Colors.YELLOW)

def get_project_root_old():
    """Get the project root directory"""
    script_path = Path(__file__).resolve()
    return script_path.parent.parent.parent
    """Get the project root directory"""
    script_path = Path(__file__).resolve()
    return script_path.parent.parent.parent

def check_and_install_missing_packages(venv_python, backend_dir):
    """
    Check for missing packages in requirements.txt and install them.
    Returns True if any packages were installed.
    """
    requirements_file = backend_dir / "requirements.txt"
    if not requirements_file.exists():
        return False
    
    print_colored("🔍 Checking for missing packages...", Colors.BLUE)
    
    # Get list of installed packages
    try:
        result = subprocess.run(
            [str(venv_python), "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            cwd=backend_dir
        )
        installed_raw = result.stdout.strip().split('\n') if result.stdout.strip() else []
        # Create dict of installed packages (lowercase name -> version)
        installed = {}
        for line in installed_raw:
            if '==' in line:
                name, version = line.split('==', 1)
                installed[name.lower().replace('-', '_')] = version
            elif line.strip():
                # Handle packages without version
                installed[line.lower().replace('-', '_')] = ''
    except Exception as e:
        print_colored(f"⚠️  Could not check installed packages: {e}", Colors.YELLOW)
        return False
    
    # Parse requirements.txt to find required packages
    missing_packages = []
    try:
        with open(requirements_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Extract package name (handle >=, ==, [extras], etc.)
                # Examples: pandas>=2.0.0, pydantic[email], torch>=2.0.0
                import re
                match = re.match(r'^([a-zA-Z0-9_-]+)', line.replace('[', ' ').split()[0])
                if match:
                    pkg_name = match.group(1).lower().replace('-', '_')
                    if pkg_name not in installed:
                        missing_packages.append(line)
    except Exception as e:
        print_colored(f"⚠️  Could not parse requirements.txt: {e}", Colors.YELLOW)
        return False
    
    if missing_packages:
        print_colored(f"📦 Found {len(missing_packages)} missing package(s):", Colors.YELLOW)
        for pkg in missing_packages[:5]:  # Show first 5
            print_colored(f"   • {pkg}", Colors.YELLOW)
        if len(missing_packages) > 5:
            print_colored(f"   ... and {len(missing_packages) - 5} more", Colors.YELLOW)
        
        print_colored("📥 Installing missing packages...", Colors.BLUE)
        try:
            # Install missing packages
            subprocess.run(
                [str(venv_python), "-m", "pip", "install"] + missing_packages,
                cwd=backend_dir,
                check=True
            )
            print_colored(f"✅ Installed {len(missing_packages)} package(s)", Colors.GREEN)
            return True
        except subprocess.CalledProcessError as e:
            print_colored(f"⚠️  Some packages failed to install. Running full requirements install...", Colors.YELLOW)
            subprocess.run(
                [str(venv_python), "-m", "pip", "install", "-r", "requirements.txt"],
                cwd=backend_dir
            )
            return True
    else:
        print_colored("✅ All packages are installed", Colors.GREEN)
        return False


def start_backend(project_root, local_ip, backend_port=DEFAULT_BACKEND_PORT, frontend_port=DEFAULT_FRONTEND_PORT):
    """Start the backend server"""
    backend_dir = project_root / "backend"
    print_colored(f"🔧 Starting backend from: {backend_dir}", Colors.BLUE)
    
    # Check if venv exists and is valid
    venv_dir = backend_dir / "venv"
    venv_python = venv_dir / "Scripts" / "python.exe"
    venv_needs_recreation = False
    
    if not venv_python.exists():
        print_colored("⚠️  Virtual environment not found. Creating...", Colors.YELLOW)
        venv_needs_recreation = True
    else:
        # Test if venv Python is valid (not from another machine)
        try:
            result = subprocess.run([str(venv_python), "--version"], 
                                  capture_output=True, 
                                  timeout=5,
                                  cwd=backend_dir)
            if result.returncode != 0:
                print_colored("⚠️  Virtual environment is invalid (from another machine). Recreating...", Colors.YELLOW)
                venv_needs_recreation = True
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            print_colored("⚠️  Virtual environment is broken. Recreating...", Colors.YELLOW)
            venv_needs_recreation = True
    
    if venv_needs_recreation:
        # Delete old venv if it exists
        if venv_dir.exists():
            print_colored("🧹 Removing old virtual environment...", Colors.YELLOW)
            import shutil
            shutil.rmtree(venv_dir)
        
        # Create new venv
        print_colored("🔨 Creating fresh virtual environment...", Colors.BLUE)
        subprocess.run([sys.executable, "-m", "venv", "venv"], cwd=backend_dir, check=True)
        print_colored("📦 Installing backend dependencies...", Colors.BLUE)
        subprocess.run([str(venv_python), "-m", "pip", "install", "-r", "requirements.txt"], 
                      cwd=backend_dir, check=True)
    else:
        # Venv exists and is valid - check for missing packages
        check_and_install_missing_packages(venv_python, backend_dir)
    
    # Set up environment with CORS origins including LAN IP
    import json
    env = os.environ.copy()
    cors_origins = [
        f"http://localhost:{frontend_port}",
        f"http://localhost:{backend_port}", 
        f"http://127.0.0.1:{frontend_port}",
        f"http://127.0.0.1:{backend_port}",
        f"http://{local_ip}:{frontend_port}",
        f"http://{local_ip}:{backend_port}"
    ]
    env["CORS_ORIGINS"] = json.dumps(cors_origins)
    env["BACKEND_PORT"] = str(backend_port)
    env["FRONTEND_PORT"] = str(frontend_port)
    # Note: BASE_URL intentionally NOT set - will auto-detect from request
    
    # Start backend
    print_colored(f"✅ Backend starting on http://0.0.0.0:{backend_port}", Colors.GREEN)
    print_colored(f"   CORS enabled for: {local_ip}", Colors.BLUE)
    print_colored("   🔄 BASE_URL will auto-detect (no .env needed)", Colors.BLUE)
    backend_process = subprocess.Popen(
        [str(venv_python), "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", str(backend_port)],
        cwd=backend_dir,
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
    )
    
    return backend_process

def start_frontend(project_root, backend_url, npm_cmd="npm", backend_port=DEFAULT_BACKEND_PORT, frontend_port=DEFAULT_FRONTEND_PORT):
    """Start the frontend server"""
    frontend_dir = project_root / "ui"
    print_colored(f"🎨 Starting frontend from: {frontend_dir}", Colors.BLUE)
    
    # Check if node_modules exists
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print_colored("📦 Installing frontend dependencies...", Colors.BLUE)
        subprocess.run([npm_cmd, "install", "--legacy-peer-deps"], cwd=frontend_dir, check=True)
    
    # Clear Next.js cache to ensure fresh environment variables
    next_dir = frontend_dir / ".next"
    if next_dir.exists():
        print_colored("🧹 Clearing Next.js cache for fresh environment...", Colors.YELLOW)
        import shutil
        try:
            shutil.rmtree(next_dir)
            print_colored("✅ Cache cleared", Colors.GREEN)
        except Exception as e:
            print_colored(f"⚠️  Could not clear cache: {e}", Colors.YELLOW)
    
    # Set port environment variables for frontend
    env = os.environ.copy()
    env["NEXT_PUBLIC_BACKEND_PORT"] = str(backend_port)
    # Note: NEXT_PUBLIC_API_URL is not set - let it auto-detect from browser location + port
    
    # Start frontend
    print_colored(f"✅ Frontend starting on http://0.0.0.0:{frontend_port}", Colors.GREEN)
    print_colored(f"   🔄 API URL will auto-detect: localhost → localhost:{backend_port}, LAN IP → <IP>:{backend_port}", Colors.BLUE)
    frontend_process = subprocess.Popen(
        [npm_cmd, "run", "dev", "--", "--hostname", "0.0.0.0", "--port", str(frontend_port)],
        cwd=frontend_dir,
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
    )
    
    return frontend_process

def cleanup(backend_process, frontend_process):
    """Gracefully shutdown both processes"""
    print()
    print_colored("🛑 Shutting down TAV Engine...", Colors.YELLOW)
    
    if sys.platform == 'win32':
        # On Windows, use taskkill to ensure all child processes are killed
        if backend_process:
            print_colored("   Stopping backend...", Colors.YELLOW)
            try:
                # Kill the process tree
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(backend_process.pid)], 
                             capture_output=True, timeout=5)
            except:
                pass
        
        if frontend_process:
            print_colored("   Stopping frontend...", Colors.YELLOW)
            try:
                # Kill the process tree
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(frontend_process.pid)], 
                             capture_output=True, timeout=5)
            except:
                pass
    else:
        # On Unix-like systems, use normal terminate/kill
        if backend_process:
            print_colored("   Stopping backend...", Colors.YELLOW)
            backend_process.terminate()
            try:
                backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend_process.kill()
        
        if frontend_process:
            print_colored("   Stopping frontend...", Colors.YELLOW)
            frontend_process.terminate()
            try:
                frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                frontend_process.kill()
    
    print_colored("✅ TAV Engine stopped", Colors.GREEN)

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="TAV Engine - Native Windows Startup Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_native.py                          # Uses default ports (5000, 3000)
  python start_native.py --backend-port 5001      # Custom backend port
  python start_native.py --frontend-port 3001     # Custom frontend port
  python start_native.py -b 5001 -f 3001          # Both custom ports
        """
    )
    parser.add_argument(
        "-b", "--backend-port",
        type=int,
        default=DEFAULT_BACKEND_PORT,
        help=f"Backend API port (default: {DEFAULT_BACKEND_PORT})"
    )
    parser.add_argument(
        "-f", "--frontend-port",
        type=int,
        default=DEFAULT_FRONTEND_PORT,
        help=f"Frontend port (default: {DEFAULT_FRONTEND_PORT})"
    )
    return parser.parse_args()


def main():
    print_banner()
    
    # Get project root first (needed for .env loading)
    project_root = get_project_root()
    
    # Load .env file from project root
    load_env_file(project_root)
    
    # Parse command-line arguments (CLI args override .env)
    args = parse_args()
    
    # Priority: CLI args > env vars > defaults
    backend_port = args.backend_port
    frontend_port = args.frontend_port
    
    # If CLI args are defaults, check environment variables
    if backend_port == DEFAULT_BACKEND_PORT and 'BACKEND_PORT' in os.environ:
        try:
            backend_port = int(os.environ['BACKEND_PORT'])
        except ValueError:
            pass
    
    if frontend_port == DEFAULT_FRONTEND_PORT and 'FRONTEND_PORT' in os.environ:
        try:
            frontend_port = int(os.environ['FRONTEND_PORT'])
        except ValueError:
            pass
    
    # Show port configuration
    if backend_port != DEFAULT_BACKEND_PORT or frontend_port != DEFAULT_FRONTEND_PORT:
        print_colored("🔧 Custom Port Configuration:", Colors.BLUE)
        print_colored(f"   Backend:  {backend_port}", Colors.GREEN)
        print_colored(f"   Frontend: {frontend_port}", Colors.GREEN)
        print()
    
    # Check dependencies
    result = check_dependencies()
    if isinstance(result, tuple):
        success, npm_cmd = result
        if not success:
            print_colored("❌ Please install missing dependencies and try again", Colors.RED)
            sys.exit(1)
    else:
        print_colored("❌ Please install missing dependencies and try again", Colors.RED)
        sys.exit(1)
    
    # Detect local IP
    local_ip = get_local_ip()
    print_colored(f"🌐 Local IP detected: {local_ip}", Colors.GREEN)
    print()
    
    # Show project root (already set earlier for .env loading)
    print_colored(f"📁 Project root: {project_root}", Colors.BLUE)
    print()
    
    # Create minimal .env files (static settings only, dynamic at runtime)
    print_colored("📝 Setting up configuration...", Colors.BLUE)
    create_minimal_env_files(project_root)
    print()
    
    backend_process = None
    frontend_process = None
    
    # Signal handler for proper cleanup
    def signal_handler(signum, frame):
        print_colored("\n\n👋 Received shutdown signal", Colors.YELLOW)
        cleanup(backend_process, frontend_process)
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    if sys.platform == 'win32':
        signal.signal(signal.SIGBREAK, signal_handler)
    else:
        signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start backend
        backend_process = start_backend(project_root, local_ip, backend_port, frontend_port)
        time.sleep(3)  # Give backend time to start
        
        # Start frontend with backend URL
        backend_url = f"http://{local_ip}:{backend_port}"
        frontend_process = start_frontend(project_root, backend_url, npm_cmd, backend_port, frontend_port)
        time.sleep(2)
        
        print()
        print_colored("=" * 60, Colors.GREEN)
        print_colored("✅ TAV Engine is running with dynamic IP detection!", Colors.GREEN)
        print_colored("=" * 60, Colors.GREEN)
        print()
        print_colored("📍 Local Access (this computer):", Colors.BLUE)
        print_colored(f"   Frontend:  http://localhost:{frontend_port}", Colors.GREEN)
        print_colored(f"   Backend:   http://localhost:{backend_port}", Colors.GREEN)
        print_colored(f"   API Docs:  http://localhost:{backend_port}/docs", Colors.GREEN)
        print()
        print_colored("🌐 LAN Access (same WiFi network):", Colors.BLUE)
        print_colored(f"   Frontend:  http://{local_ip}:{frontend_port}", Colors.GREEN)
        print_colored(f"   Backend:   http://{local_ip}:{backend_port}", Colors.GREEN)
        print_colored(f"   API Docs:  http://{local_ip}:{backend_port}/docs", Colors.GREEN)
        print()
        print_colored("🔄 Smart Features:", Colors.BLUE)
        print_colored("   ✅ Frontend auto-detects backend based on how you access it", Colors.GREEN)
        print_colored("   ✅ Email review links auto-adjust to your access method", Colors.GREEN)
        print_colored("   ✅ No .env file configuration needed!", Colors.GREEN)
        print()
        print_colored("✨ Network shares are fully accessible!", Colors.GREEN)
        print_colored("   Use Windows paths like: Z:\\folder or \\\\server\\share", Colors.GREEN)
        print()
        print_colored("Press Ctrl+C to stop", Colors.YELLOW)
        print()
        
        # Keep script running
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            if backend_process.poll() is not None:
                print_colored("❌ Backend stopped unexpectedly!", Colors.RED)
                break
            if frontend_process.poll() is not None:
                print_colored("❌ Frontend stopped unexpectedly!", Colors.RED)
                break
    
    except KeyboardInterrupt:
        print_colored("\n\n👋 Received shutdown signal", Colors.YELLOW)
    except Exception as e:
        print_colored(f"❌ Error: {e}", Colors.RED)
    finally:
        cleanup(backend_process, frontend_process)

if __name__ == "__main__":
    main()

