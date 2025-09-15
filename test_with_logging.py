#!/usr/bin/env python3
"""
Demo script to run tests with mock API logging enabled.

This shows all mock API calls made during testing for debugging purposes.
"""

import subprocess
import sys
import os

def run_tests_with_logging(test_path=None, verbose=False):
    """
    Run tests with mock API logging enabled.
    
    Args:
        test_path: Specific test path or None for all tests
        verbose: Whether to show verbose output
    """
    # Set environment variable to enable logging
    env = os.environ.copy()
    env["MOCK_API_LOGGING"] = "true"
    
    # Build pytest command
    cmd = ["uv", "run", "pytest"]
    
    if test_path:
        cmd.append(test_path)
    else:
        # Run core tests by default
        cmd.extend([
            "tests/test_cli.py",
            "tests/test_client.py",
            "tests/test_mcp_server.py",
            "tests/test_vultr_server.py",
            "tests/test_server.py"
        ])
    
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    cmd.extend(["--tb=short", "--maxfail=5"])
    
    print("="*60)
    print("RUNNING TESTS WITH MOCK API LOGGING")
    print("="*60)
    print(f"Command: {' '.join(cmd)}")
    print("="*60 + "\n")
    
    # Run the tests
    result = subprocess.run(cmd, env=env)
    
    return result.returncode

if __name__ == "__main__":
    # Check for command line arguments
    test_path = sys.argv[1] if len(sys.argv) > 1 else None
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python test_with_logging.py [test_path] [--verbose]")
        print("\nExamples:")
        print("  python test_with_logging.py")
        print("  python test_with_logging.py tests/test_client.py")
        print("  python test_with_logging.py tests/test_client.py::TestVultrDNSClient -v")
        sys.exit(0)
    
    exit_code = run_tests_with_logging(test_path, verbose)
    sys.exit(exit_code)