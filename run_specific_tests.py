#!/usr/bin/env python3
"""Run specific tests to identify failures."""

import subprocess
import sys
import os

def run_test_subset(test_file, pattern=""):
    """Run a subset of tests."""
    cmd = [
        sys.executable, "-m", "pytest", 
        test_file,
        "-v", 
        "--tb=short",
        "--no-cov"  # Disable coverage for faster runs
    ]
    
    if pattern:
        cmd.extend(["-k", pattern])
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd="/home/rpm/claude/mcp-vultr",
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(f"Return code: {result.returncode}")
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("Test timed out!")
        return False
    except Exception as e:
        print(f"Error running test: {e}")
        return False

def main():
    """Run specific test categories."""
    print("=" * 60)
    print("Testing retry module - basic tests")
    print("=" * 60)
    
    # Test basic retry functionality first
    success1 = run_test_subset("tests/test_retry.py", "test_retryable_error")
    
    print("\n" + "=" * 60)
    print("Testing cache module - basic tests")
    print("=" * 60)
    
    # Test basic cache functionality
    success2 = run_test_subset("tests/test_cache.py", "test_init_default")
    
    print("\n" + "=" * 60)
    print("Testing retry module - async tests")
    print("=" * 60)
    
    # Test async retry functionality
    success3 = run_test_subset("tests/test_retry.py", "test_successful_call_no_retry")
    
    print("\n" + "=" * 60)
    print("Testing cache module - decorator tests")
    print("=" * 60)
    
    # Test cache decorator
    success4 = run_test_subset("tests/test_cache.py", "test_decorator_basic_usage")
    
    if all([success1, success2, success3, success4]):
        print("\n✓ All basic tests passed!")
        
        # Run full test suites
        print("\n" + "=" * 60)
        print("Running full retry test suite")
        print("=" * 60)
        success_retry = run_test_subset("tests/test_retry.py")
        
        print("\n" + "=" * 60)
        print("Running full cache test suite")
        print("=" * 60)
        success_cache = run_test_subset("tests/test_cache.py")
        
        if success_retry and success_cache:
            print("\n🎉 All tests passed!")
        else:
            print(f"\n❌ Some tests failed. Retry: {'✓' if success_retry else '✗'}, Cache: {'✓' if success_cache else '✗'}")
    else:
        print(f"\n❌ Basic tests failed: {[success1, success2, success3, success4]}")

if __name__ == "__main__":
    main()