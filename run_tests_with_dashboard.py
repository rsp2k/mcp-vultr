#!/usr/bin/env python3
"""
Comprehensive Test Runner with Beautiful Dashboard Generation

This script:
1. Fixes coverage configuration (currently showing 9% incorrectly)
2. Runs comprehensive test suite with proper coverage
3. Generates unified HTML dashboard combining all reports
4. Adds historical trend tracking with SQLite
5. Creates enterprise-grade visualization

Usage:
    python run_tests_with_dashboard.py --all-checks
    python run_tests_with_dashboard.py --fast
    python run_tests_with_dashboard.py --coverage-only
    python run_tests_with_dashboard.py --dashboard-only
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from dashboard_generator import DashboardGenerator


class TestRunner:
    """Enterprise-grade test runner with beautiful dashboard generation."""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.reports_dir = self.project_root / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
    def run_comprehensive_tests(self, mode: str = "all") -> dict:
        """Run comprehensive test suite with proper configuration."""
        print("🧪 Running comprehensive test suite...")
        
        if mode == "fast":
            return self.run_fast_tests()
        elif mode == "coverage":
            return self.run_coverage_tests()
        elif mode == "dashboard":
            return self.generate_dashboard_only()
        else:
            return self.run_all_tests()
    
    def fix_coverage_configuration(self):
        """Fix coverage configuration to show accurate results."""
        print("🔧 Fixing coverage configuration...")
        
        # Create comprehensive .coveragerc
        coveragerc_content = """[run]
source = src/mcp_vultr
omit = 
    */tests/*
    */test_*
    */__pycache__/*
    */venv/*
    */build/*
    */dist/*
    */htmlcov/*
    src/mcp_vultr/__main__.py
    src/mcp_vultr/_version.py
    setup.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    if self.debug:
    if settings.DEBUG
    raise AssertionError
    raise NotImplementedError
    if 0:
    if __name__ == .__main__.:
    class.*\\bProtocol\\):
    @(abc\\.)?abstractmethod

show_missing = True
skip_covered = False
precision = 1

[html]
directory = htmlcov
show_contexts = True
skip_covered = False
"""
        
        coveragerc_path = self.project_root / ".coveragerc"
        coveragerc_path.write_text(coveragerc_content)
        print(f"✅ Coverage configuration updated: {coveragerc_path}")
        
        return coveragerc_path
    
    def run_fast_tests(self) -> dict:
        """Run fast tests without coverage for quick feedback."""
        print("⚡ Running fast tests...")
        
        start_time = time.time()
        
        cmd = [
            "uv", "run", "pytest",
            "-m", "not slow",
            "--no-cov",
            "--tb=short",
            "--maxfail=10",
            "-q",
            f"--junitxml={self.reports_dir}/junit-fast.xml"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
        duration = time.time() - start_time
        
        return {
            "mode": "fast",
            "returncode": result.returncode,
            "duration": duration,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    
    def run_coverage_tests(self) -> dict:
        """Run tests with comprehensive coverage reporting."""
        print("📊 Running tests with coverage analysis...")
        
        # Fix coverage configuration first
        self.fix_coverage_configuration()
        
        start_time = time.time()
        
        # Run tests with coverage
        cmd = [
            "uv", "run", "pytest",
            "--cov=src/mcp_vultr",
            "--cov-report=html",
            "--cov-report=xml",
            "--cov-report=json",
            "--cov-report=term-missing",
            "--cov-fail-under=0",  # Don't fail on low coverage, just report
            "--tb=short",
            f"--junitxml={self.reports_dir}/junit-coverage.xml",
            "tests/"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
        duration = time.time() - start_time
        
        # Parse coverage results
        coverage_data = self.parse_coverage_results()
        
        return {
            "mode": "coverage",
            "returncode": result.returncode,
            "duration": duration,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "coverage": coverage_data
        }
    
    def run_all_tests(self) -> dict:
        """Run comprehensive test suite with all checks."""
        print("🔍 Running comprehensive test suite with all checks...")
        
        # Fix coverage configuration
        self.fix_coverage_configuration()
        
        start_time = time.time()
        
        # Run comprehensive tests
        cmd = [
            "uv", "run", "pytest",
            "--cov=src/mcp_vultr",
            "--cov-report=html",
            "--cov-report=xml", 
            "--cov-report=json",
            "--cov-report=term-missing",
            "--tb=long",
            "--maxfail=20",
            "--timeout=60",
            f"--junitxml={self.reports_dir}/junit-comprehensive.xml",
            "-v",
            "tests/"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
        duration = time.time() - start_time
        
        # Run additional quality checks
        quality_results = self.run_quality_checks()
        
        # Parse all results
        coverage_data = self.parse_coverage_results()
        test_results = self.parse_test_results()
        
        return {
            "mode": "comprehensive",
            "returncode": result.returncode,
            "duration": duration,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "coverage": coverage_data,
            "tests": test_results,
            "quality": quality_results
        }
    
    def run_quality_checks(self) -> dict:
        """Run code quality checks (ruff, mypy, etc.)."""
        print("🔍 Running code quality checks...")
        
        quality_results = {}
        
        # Run ruff check
        try:
            result = subprocess.run(
                ["uv", "run", "ruff", "check", "src/", "--output-format=json"],
                capture_output=True, text=True, cwd=self.project_root
            )
            quality_results["ruff"] = {
                "returncode": result.returncode,
                "issues": json.loads(result.stdout) if result.stdout else []
            }
        except Exception as e:
            quality_results["ruff"] = {"error": str(e)}
        
        # Run mypy check  
        try:
            result = subprocess.run(
                ["uv", "run", "mypy", "src/mcp_vultr", "--json-report", str(self.reports_dir / "mypy.json")],
                capture_output=True, text=True, cwd=self.project_root
            )
            quality_results["mypy"] = {
                "returncode": result.returncode,
                "output": result.stdout
            }
        except Exception as e:
            quality_results["mypy"] = {"error": str(e)}
        
        return quality_results
    
    def parse_coverage_results(self) -> dict:
        """Parse coverage results from multiple sources."""
        coverage_data = {
            "overall_percentage": 0,
            "total_statements": 0,
            "missing_statements": 0,
            "modules": []
        }
        
        # Try to parse coverage.json
        coverage_json_path = self.project_root / "coverage.json"
        if coverage_json_path.exists():
            try:
                with open(coverage_json_path) as f:
                    data = json.load(f)
                    
                # Extract summary
                totals = data.get("totals", {})
                coverage_data["total_statements"] = totals.get("num_statements", 0)
                coverage_data["missing_statements"] = totals.get("missing_lines", 0) 
                coverage_data["overall_percentage"] = round(totals.get("percent_covered", 0), 1)
                
                # Extract module data
                files = data.get("files", {})
                for file_path, file_data in files.items():
                    # Skip test files and __pycache__
                    if "/test" in file_path or "__pycache__" in file_path:
                        continue
                        
                    summary = file_data.get("summary", {})
                    statements = summary.get("num_statements", 0)
                    missing = summary.get("missing_lines", 0)
                    coverage_pct = round(summary.get("percent_covered", 0), 1)
                    
                    status = "excellent" if coverage_pct >= 90 else \
                             "good" if coverage_pct >= 80 else \
                             "warning" if coverage_pct >= 70 else "critical"
                    
                    coverage_data["modules"].append({
                        "name": file_path,
                        "statements": statements,
                        "missing": missing,
                        "coverage": coverage_pct,
                        "status": status
                    })
                    
            except Exception as e:
                print(f"Warning: Could not parse coverage.json: {e}")
        
        return coverage_data
    
    def parse_test_results(self) -> dict:
        """Parse test results from JUnit XML."""
        junit_files = list(self.reports_dir.glob("junit-*.xml"))
        if not junit_files:
            return {"total": 0, "passed": 0, "failed": 0, "skipped": 0}
        
        # Use the most recent JUnit file
        junit_file = max(junit_files, key=lambda f: f.stat().st_mtime)
        
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(junit_file)
            root = tree.getroot()
            
            total = int(root.get('tests', 0))
            failures = int(root.get('failures', 0))
            errors = int(root.get('errors', 0))
            skipped = int(root.get('skipped', 0))
            passed = total - failures - errors - skipped
            time_taken = float(root.get('time', 0))
            
            return {
                "total": total,
                "passed": passed,
                "failed": failures + errors,
                "skipped": skipped,
                "duration": time_taken,
                "success_rate": round((passed / total * 100) if total > 0 else 0, 1)
            }
        except Exception as e:
            print(f"Warning: Could not parse JUnit XML: {e}")
            return {"total": 0, "passed": 0, "failed": 0, "skipped": 0}
    
    def generate_dashboard_only(self) -> dict:
        """Generate dashboard from existing test results."""
        print("📊 Generating dashboard from existing results...")
        
        start_time = time.time()
        
        # Generate dashboard
        generator = DashboardGenerator(self.project_root)
        dashboard_path = generator.generate_dashboard()
        
        duration = time.time() - start_time
        
        return {
            "mode": "dashboard-only",
            "returncode": 0,
            "duration": duration,
            "dashboard_path": dashboard_path
        }
    
    def generate_dashboard(self, test_results: dict = None):
        """Generate the beautiful HTML dashboard."""
        print("🎨 Generating enterprise-grade HTML dashboard...")
        
        generator = DashboardGenerator(self.project_root)
        dashboard_path = generator.generate_dashboard()
        
        print(f"✅ Dashboard generated: {dashboard_path}")
        return dashboard_path
    
    def print_summary(self, results: dict):
        """Print test execution summary."""
        mode = results.get("mode", "unknown")
        returncode = results.get("returncode", 1)
        duration = results.get("duration", 0)
        
        print("\n" + "="*60)
        print(f"🧪 TEST EXECUTION SUMMARY ({mode.upper()})")
        print("="*60)
        
        if returncode == 0:
            print("✅ Status: PASSED")
        else:
            print("❌ Status: FAILED")
        
        print(f"⏱️  Duration: {duration:.1f}s")
        
        # Print coverage summary if available
        if "coverage" in results:
            coverage = results["coverage"]
            print(f"📊 Coverage: {coverage.get('overall_percentage', 0)}%")
            print(f"📝 Total Statements: {coverage.get('total_statements', 0)}")
            print(f"❗ Missing Coverage: {coverage.get('missing_statements', 0)}")
        
        # Print test summary if available
        if "tests" in results:
            tests = results["tests"]
            print(f"🧪 Total Tests: {tests.get('total', 0)}")
            print(f"✅ Passed: {tests.get('passed', 0)}")
            print(f"❌ Failed: {tests.get('failed', 0)}")
            print(f"⏭️  Skipped: {tests.get('skipped', 0)}")
            print(f"📈 Success Rate: {tests.get('success_rate', 0)}%")
        
        print("="*60)
        
        # Print dashboard path if generated
        if "dashboard_path" in results:
            print(f"🎨 Dashboard: {results['dashboard_path']}")
            print("="*60)


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Comprehensive Test Runner with Beautiful Dashboard"
    )
    
    parser.add_argument(
        "--fast", 
        action="store_true",
        help="Run fast tests without coverage"
    )
    
    parser.add_argument(
        "--coverage-only",
        action="store_true", 
        help="Run tests with coverage analysis"
    )
    
    parser.add_argument(
        "--dashboard-only",
        action="store_true",
        help="Generate dashboard from existing results"
    )
    
    parser.add_argument(
        "--all-checks",
        action="store_true",
        help="Run comprehensive tests with all quality checks (default)"
    )
    
    args = parser.parse_args()
    
    # Determine mode
    if args.fast:
        mode = "fast"
    elif args.coverage_only:
        mode = "coverage"
    elif args.dashboard_only:
        mode = "dashboard"
    else:
        mode = "all"  # Default to comprehensive
    
    # Run tests
    runner = TestRunner()
    
    try:
        results = runner.run_comprehensive_tests(mode)
        
        # Generate dashboard unless it's fast mode
        if mode != "fast":
            dashboard_path = runner.generate_dashboard(results)
            results["dashboard_path"] = dashboard_path
        
        # Print summary
        runner.print_summary(results)
        
        # Exit with appropriate code
        sys.exit(results.get("returncode", 0))
        
    except KeyboardInterrupt:
        print("\n❌ Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()