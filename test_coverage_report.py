#!/usr/bin/env python3
"""
Test script to check coverage of retry.py and cache.py modules specifically.
"""

import subprocess
import sys
from pathlib import Path

def run_coverage_test():
    """Run tests with coverage for specific modules."""
    
    # Change to package directory
    package_dir = Path(__file__).parent
    
    print("🧪 Running coverage tests for retry.py and cache.py modules...")
    print("=" * 60)
    
    # Command to run tests with coverage for specific modules
    cmd = [
        "uv", "run", "pytest", 
        "tests/test_retry.py", 
        "tests/test_cache.py",
        "--cov=mcp_vultr.retry",
        "--cov=mcp_vultr.cache",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "-v"
    ]
    
    try:
        result = subprocess.run(cmd, cwd=package_dir, check=False, capture_output=False)
        
        if result.returncode == 0:
            print("\n✅ All tests passed!")
            print("\n📊 Coverage report saved to htmlcov/index.html")
            return True
        else:
            print(f"\n❌ Tests failed with return code: {result.returncode}")
            return False
            
    except FileNotFoundError:
        print("❌ uv not found. Please install uv or run tests with pytest directly.")
        print("Alternative command: pytest tests/test_retry.py tests/test_cache.py --cov=mcp_vultr.retry --cov=mcp_vultr.cache --cov-report=term-missing -v")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

if __name__ == "__main__":
    success = run_coverage_test()
    sys.exit(0 if success else 1)