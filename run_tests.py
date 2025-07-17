#!/usr/bin/env python3
"""
Comprehensive test runner for the Vultr DNS MCP package.

This script runs all tests and provides detailed reporting following
FastMCP testing best practices.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(test_type="all", verbose=False, coverage=False, fast=False):
    """Run tests with specified options."""
    
    # Change to package directory
    package_dir = Path(__file__).parent
    
    # Base pytest command using uv run
    cmd = ["uv", "run", "pytest"]
    
    # Add verbosity
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    # Add coverage if requested
    if coverage:
        cmd.extend(["--cov=mcp_vultr", "--cov-report=term-missing", "--cov-report=html"])
    
    # Select tests based on type
    if test_type == "unit":
        cmd.extend(["-m", "unit"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    elif test_type == "mcp":
        cmd.extend(["-m", "mcp"])
    elif test_type == "fast":
        cmd.extend(["-m", "not slow"])
    elif test_type == "slow":
        cmd.extend(["-m", "slow"])
    elif test_type != "all":
        print(f"Unknown test type: {test_type}")
        return False
    
    # Skip slow tests if fast mode
    if fast and test_type == "all":
        cmd.extend(["-m", "not slow"])
    
    # Add test directory
    cmd.append("tests/")
    
    print("🧪 Running Vultr DNS MCP Tests")
    print("=" * 50)
    print(f"📋 Test type: {test_type}")
    print(f"🚀 Command: {' '.join(cmd)}")
    print()
    
    try:
        # Run the tests
        result = subprocess.run(cmd, cwd=package_dir, check=False)
        
        if result.returncode == 0:
            print("\n✅ All tests passed!")
            if coverage:
                print("📊 Coverage report generated in htmlcov/")
        else:
            print(f"\n❌ Tests failed with exit code {result.returncode}")
        
        return result.returncode == 0
        
    except FileNotFoundError:
        print("❌ Error: pytest not found. Install with: uv add pytest")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False


def run_linting():
    """Run code quality checks."""
    print("\n🔍 Running Code Quality Checks")
    print("=" * 50)
    
    checks = [
        (["uv", "run", "black", "--check", "src", "tests"], "Black formatting"),
        (["uv", "run", "isort", "--check", "src", "tests"], "Import sorting"),
        (["uv", "run", "flake8", "src", "tests"], "Flake8 linting"),
        (["uv", "run", "mypy", "src"], "Type checking")
    ]
    
    all_passed = True
    
    for cmd, name in checks:
        print(f"Running {name}...")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"  ✅ {name} passed")
            else:
                print(f"  ❌ {name} failed:")
                print(f"     {result.stdout}")
                print(f"     {result.stderr}")
                all_passed = False
        except FileNotFoundError:
            print(f"  ⚠️  {name} skipped (tool not installed)")
        except Exception as e:
            print(f"  ❌ {name} error: {e}")
            all_passed = False
    
    return all_passed


def run_package_validation():
    """Run package validation checks."""
    print("\n📦 Running Package Validation")
    print("=" * 50)
    
    # Test imports
    print("Testing package imports...")
    try:
        import sys
        from pathlib import Path
        
        # Add src to path
        src_path = Path(__file__).parent / "src"
        sys.path.insert(0, str(src_path))
        
        # Test main imports
        from mcp_vultr import VultrDNSClient, VultrDNSServer, create_mcp_server
        from mcp_vultr._version import __version__
        
        print(f"  ✅ Package imports successful (version {__version__})")
        
        # Test MCP server creation
        server = create_mcp_server("test-key")
        print("  ✅ MCP server creation successful")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Package validation failed: {e}")
        return False


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run Vultr DNS MCP tests")
    parser.add_argument(
        "--type", 
        choices=["all", "unit", "integration", "mcp", "fast", "slow"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--coverage", "-c",
        action="store_true", 
        help="Generate coverage report"
    )
    parser.add_argument(
        "--fast", "-f",
        action="store_true",
        help="Skip slow tests"
    )
    parser.add_argument(
        "--lint", "-l",
        action="store_true",
        help="Run code quality checks"
    )
    parser.add_argument(
        "--validate", 
        action="store_true",
        help="Run package validation"
    )
    parser.add_argument(
        "--all-checks",
        action="store_true",
        help="Run tests, linting, and validation"
    )
    
    args = parser.parse_args()
    
    success = True
    
    # Run package validation first if requested
    if args.validate or args.all_checks:
        if not run_package_validation():
            success = False
    
    # Run tests
    if not args.lint or args.all_checks:
        if not run_tests(args.type, args.verbose, args.coverage, args.fast):
            success = False
    
    # Run linting if requested
    if args.lint or args.all_checks:
        if not run_linting():
            success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All checks passed!")
        print("\n📚 Next steps:")
        print("  • Run 'uv build' to build the package")
        print("  • Run 'uv run twine check dist/*' to validate")
        print("  • Upload to PyPI with 'uv run twine upload dist/*'")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
