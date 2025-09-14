#!/usr/bin/env python3
"""
TUI Test Runner Script.

Convenient script for running different categories of TUI tests
with appropriate configurations and reporting.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and return the result."""
    if description:
        print(f"\n🚀 {description}")
        print("-" * 60)
    
    start_time = time.time()
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    duration = time.time() - start_time
    
    if result.returncode == 0:
        print(f"✅ Success ({duration:.1f}s)")
        if result.stdout.strip():
            print(result.stdout)
    else:
        print(f"❌ Failed ({duration:.1f}s)")
        if result.stderr.strip():
            print(result.stderr)
        if result.stdout.strip():
            print(result.stdout)
    
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Run TUI tests with various options")
    parser.add_argument("--quick", action="store_true", 
                       help="Run only fast unit tests")
    parser.add_argument("--unit", action="store_true",
                       help="Run TUI unit tests")
    parser.add_argument("--integration", action="store_true", 
                       help="Run TUI integration tests")
    parser.add_argument("--snapshots", action="store_true",
                       help="Run TUI snapshot tests")
    parser.add_argument("--performance", action="store_true",
                       help="Run TUI performance tests")
    parser.add_argument("--update-snapshots", action="store_true",
                       help="Update snapshot references")
    parser.add_argument("--coverage", action="store_true",
                       help="Run with coverage reporting")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    parser.add_argument("--parallel", "-n", type=int, default=1,
                       help="Number of parallel workers")
    
    args = parser.parse_args()
    
    # Base pytest command
    base_cmd = "uv run pytest"
    
    # Build command based on arguments
    if args.quick:
        cmd = f"{base_cmd} -m 'tui_unit and fast' tests/test_tui_app.py"
        description = "Running Quick TUI Unit Tests"
    elif args.unit:
        cmd = f"{base_cmd} -m tui_unit tests/test_tui_app.py"
        description = "Running TUI Unit Tests"
    elif args.integration:
        cmd = f"{base_cmd} -m tui_integration tests/test_tui_app.py"
        description = "Running TUI Integration Tests"
    elif args.snapshots:
        cmd = f"{base_cmd} -m tui_snapshot tests/test_tui_snapshots.py"
        description = "Running TUI Snapshot Tests"
    elif args.performance:
        cmd = f"{base_cmd} -m tui_performance tests/test_tui_app.py"
        description = "Running TUI Performance Tests"
    else:
        # Run all TUI tests
        cmd = f"{base_cmd} -m tui tests/test_tui_app.py tests/test_tui_snapshots.py"
        description = "Running All TUI Tests"
    
    # Add coverage if requested
    if args.coverage:
        cmd += " --cov=mcp_vultr.tui_app --cov-report=html --cov-report=term"
    
    # Add verbose if requested
    if args.verbose:
        cmd += " -v"
    
    # Add parallel execution if requested
    if args.parallel > 1:
        cmd += f" -n {args.parallel}"
    
    # Update snapshots if requested
    if args.update_snapshots:
        cmd += " --snapshot-update"
        description += " (Updating Snapshots)"
    
    # Show test configuration
    print("🧪 TUI Test Runner")
    print("=" * 60)
    print(f"Command: {cmd}")
    print(f"Working Directory: {Path.cwd()}")
    print()
    
    # Run the tests
    success = run_command(cmd, description)
    
    if success:
        print("\n🎉 All tests passed successfully!")
        
        # Show coverage report location if generated
        if args.coverage:
            coverage_path = Path("htmlcov/index.html")
            if coverage_path.exists():
                print(f"📊 Coverage report: {coverage_path.absolute()}")
        
        # Show snapshot location if snapshots were run
        if args.snapshots or not any([args.quick, args.unit, args.integration, args.performance]):
            snapshot_path = Path("tests/__snapshots__")
            if snapshot_path.exists():
                snapshot_count = len(list(snapshot_path.glob("*.txt")))
                print(f"📸 {snapshot_count} snapshots in: {snapshot_path.absolute()}")
        
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        print("\nDebugging tips:")
        print("- Run with --verbose for more details")
        print("- Check specific test categories with --unit, --integration, etc.")
        print("- Update snapshots with --update-snapshots if visual changes are expected")
        sys.exit(1)


if __name__ == "__main__":
    main()