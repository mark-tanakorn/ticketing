# """
# Unit Test Runner

# Simple script to run all unit tests and display results.
# """

# import sys
# import os

# # Add the backend directory to the path so we can import app modules
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# def run_unit_tests():
#     """Run all unit tests in the tests/unit directory."""
#     try:
#         import pytest
#     except ImportError:
#         print("❌ pytest is not installed. Please install it first:")
#         print("   pip install pytest pytest-asyncio pytest-cov")
#         return 1
    
#     print("=" * 70)
#     print("🧪 Running Unit Tests")
#     print("=" * 70)
#     print()
    
#     # Get the test directory
#     test_dir = os.path.join(os.path.dirname(__file__), "unit")
    
#     # Run pytest programmatically
#     args = [
#         test_dir,           # Test directory
#         "-v",               # Verbose
#         "--tb=short",       # Short traceback format
#         "--color=yes",      # Colored output
#         "-x",               # Stop on first failure (optional, remove if you want to see all failures)
#     ]
    
#     print(f"📂 Test Directory: {test_dir}")
#     print(f"🔍 Discovering and running tests...\n")
    
#     exit_code = pytest.main(args)
    
#     print()
#     print("=" * 70)
#     if exit_code == 0:
#         print("✅ All tests passed!")
#     else:
#         print("❌ Some tests failed. See details above.")
#     print("=" * 70)
    
#     return exit_code


# if __name__ == "__main__":
#     sys.exit(run_unit_tests())

