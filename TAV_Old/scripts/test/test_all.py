#!/usr/bin/env python3
"""
Unified Test Runner for TAV Opensource
Runs all tests (backend + frontend) and provides a comprehensive report.
"""

import subprocess
import sys
import time
from pathlib import Path

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_section(title):
    """Print a section header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{title:^70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

def run_command(cmd, cwd=None, description=""):
    """Run a command and return success status"""
    print(f"{Colors.OKCYAN}▶ {description}{Colors.ENDC}")
    print(f"  Command: {' '.join(cmd)}")
    
    start_time = time.time()
    result = subprocess.run(cmd, cwd=cwd, capture_output=False)
    elapsed = time.time() - start_time
    
    if result.returncode == 0:
        print(f"{Colors.OKGREEN}✓ {description} passed ({elapsed:.2f}s){Colors.ENDC}")
        return True
    else:
        print(f"{Colors.FAIL}✗ {description} failed ({elapsed:.2f}s){Colors.ENDC}")
        return False

def main():
    # Script is in scripts/, so root is one level up
    root = Path(__file__).parent.parent
    backend_dir = root / "backend"
    frontend_dir = root / "ui"
    
    results = {}
    
    print(f"\n{Colors.BOLD}🧪 TAV Opensource - Comprehensive Test Suite{Colors.ENDC}")
    print(f"{Colors.BOLD}Running all tests for backend and frontend...{Colors.ENDC}")
    
    # Backend Tests
    print_section("Backend Tests")
    
    if backend_dir.exists():
        # Unit tests
        results['backend_unit'] = run_command(
            ["python", "-m", "pytest", "tests/unit", "-v", "--tb=short"],
            cwd=backend_dir,
            description="Backend Unit Tests"
        )
        
        # Coverage report
        results['backend_coverage'] = run_command(
            ["python", "-m", "pytest", "tests/unit", "--cov=app", "--cov-report=term", "-q"],
            cwd=backend_dir,
            description="Backend Coverage Report"
        )
    else:
        print(f"{Colors.WARNING}⚠ Backend directory not found{Colors.ENDC}")
        results['backend_unit'] = False
        results['backend_coverage'] = False
    
    # Frontend Tests
    print_section("Frontend Tests")
    
    if frontend_dir.exists():
        # Install dependencies if needed
        if not (frontend_dir / "node_modules").exists():
            print(f"{Colors.WARNING}Installing frontend dependencies...{Colors.ENDC}")
            run_command(
                ["npm", "ci"],
                cwd=frontend_dir,
                description="Install Frontend Dependencies"
            )
        
        # Run tests
        results['frontend_tests'] = run_command(
            ["npm", "test", "--", "--passWithNoTests"],
            cwd=frontend_dir,
            description="Frontend Tests"
        )
        
        # Type check
        results['frontend_typecheck'] = run_command(
            ["npx", "tsc", "--noEmit"],
            cwd=frontend_dir,
            description="Frontend Type Check"
        )
    else:
        print(f"{Colors.WARNING}⚠ Frontend directory not found{Colors.ENDC}")
        results['frontend_tests'] = False
        results['frontend_typecheck'] = False
    
    # Summary
    print_section("Test Summary")
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    print(f"{Colors.BOLD}Results:{Colors.ENDC}")
    for test_name, passed in results.items():
        status = f"{Colors.OKGREEN}✓ PASS{Colors.ENDC}" if passed else f"{Colors.FAIL}✗ FAIL{Colors.ENDC}"
        print(f"  {test_name:30} {status}")
    
    print(f"\n{Colors.BOLD}Overall: {passed_tests}/{total_tests} test suites passed{Colors.ENDC}")
    
    if passed_tests == total_tests:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}🎉 All tests passed! Safe to deploy.{Colors.ENDC}")
        return 0
    else:
        print(f"\n{Colors.FAIL}{Colors.BOLD}❌ Some tests failed. Please fix before deploying.{Colors.ENDC}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

