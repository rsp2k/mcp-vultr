#!/usr/bin/env python3
"""
TUI Test Validation Script

This script validates that the TUI testing framework is properly configured
and all dependencies are available.
"""

import sys
import subprocess
from pathlib import Path


def check_dependency(module_name: str, import_name: str = None) -> bool:
    """Check if a Python module is available."""
    if import_name is None:
        import_name = module_name
    
    try:
        __import__(import_name)
        print(f"✅ {module_name}: Available")
        return True
    except ImportError:
        print(f"❌ {module_name}: Missing")
        return False


def check_file_exists(file_path: Path, description: str) -> bool:
    """Check if a file exists."""
    if file_path.exists():
        print(f"✅ {description}: Found")
        return True
    else:
        print(f"❌ {description}: Missing")
        return False


def check_pytest_markers() -> bool:
    """Check if pytest markers are properly configured."""
    try:
        result = subprocess.run(
            ['uv', 'run', 'pytest', '--markers'],
            capture_output=True,
            text=True,
            check=True
        )
        
        markers_output = result.stdout
        required_markers = [
            'tui:', 'tui_unit:', 'tui_integration:', 
            'tui_snapshot:', 'tui_performance:'
        ]
        
        missing_markers = []
        for marker in required_markers:
            if marker not in markers_output:
                missing_markers.append(marker.rstrip(':'))
        
        if missing_markers:
            print(f"❌ Pytest markers: Missing {missing_markers}")
            return False
        else:
            print("✅ Pytest markers: All TUI markers configured")
            return True
            
    except subprocess.CalledProcessError:
        print("❌ Pytest markers: Unable to check (pytest not working)")
        return False


def check_test_discovery() -> bool:
    """Check if TUI tests are discoverable."""
    try:
        result = subprocess.run(
            ['uv', 'run', 'pytest', '--collect-only', '-m', 'tui'],
            capture_output=True,
            text=True,
            check=True
        )
        
        if 'test_tui' in result.stdout:
            print("✅ Test discovery: TUI tests found")
            return True
        else:
            print("❌ Test discovery: No TUI tests found")
            return False
            
    except subprocess.CalledProcessError:
        print("❌ Test discovery: Failed to collect tests")
        return False


def main():
    """Main validation function."""
    print("🔍 TUI Testing Framework Validation")
    print("=" * 50)
    
    all_checks_passed = True
    
    # Check Python dependencies
    print("\n📦 Checking Python Dependencies:")
    dependencies = [
        ('textual', 'textual'),
        ('pytest', 'pytest'),
        ('pytest-asyncio', 'pytest_asyncio'),
        ('pytest-textual-snapshot', 'pytest_textual_snapshot'),
        ('rich', 'rich'),
    ]
    
    for dep_name, import_name in dependencies:
        if not check_dependency(dep_name, import_name):
            all_checks_passed = False
    
    # Check TUI application module
    print("\n🖥️  Checking TUI Application:")
    try:
        from mcp_vultr.tui_app import VultrTUI, WelcomeScreen, MCPSetupScreen, APIShowcaseScreen, HelpScreen
        print("✅ TUI modules: All imports successful")
    except ImportError as e:
        print(f"❌ TUI modules: Import failed - {e}")
        all_checks_passed = False
    
    # Check test files
    print("\n📄 Checking Test Files:")
    project_root = Path(__file__).parent
    test_files = [
        (project_root / 'tests' / 'test_tui_app.py', 'Main TUI tests'),
        (project_root / 'tests' / 'test_tui_performance.py', 'Performance tests'),
        (project_root / 'tests' / 'test_tui_snapshots.py', 'Snapshot tests'),
        (project_root / 'tests' / 'test_tui_conftest.py', 'TUI test configuration'),
        (project_root / 'tests' / 'snapshots', 'Snapshots directory'),
    ]
    
    for file_path, description in test_files:
        if not check_file_exists(file_path, description):
            all_checks_passed = False
    
    # Check pytest configuration
    print("\n⚙️  Checking Pytest Configuration:")
    if not check_pytest_markers():
        all_checks_passed = False
    
    if not check_test_discovery():
        all_checks_passed = False
    
    # Check Makefile targets
    print("\n🔨 Checking Makefile Targets:")
    makefile_path = project_root / 'Makefile'
    if makefile_path.exists():
        makefile_content = makefile_path.read_text()
        makefile_targets = [
            'test-tui', 'test-tui-unit', 'test-tui-integration',
            'test-tui-snapshots', 'test-tui-performance'
        ]
        
        missing_targets = []
        for target in makefile_targets:
            if target not in makefile_content:
                missing_targets.append(target)
        
        if missing_targets:
            print(f"❌ Makefile targets: Missing {missing_targets}")
            all_checks_passed = False
        else:
            print("✅ Makefile targets: All TUI targets available")
    else:
        print("❌ Makefile: Not found")
        all_checks_passed = False
    
    # Summary
    print("\n" + "=" * 50)
    if all_checks_passed:
        print("🎉 All validation checks passed!")
        print("\n✨ TUI testing framework is ready to use!")
        print("\n📚 Quick start:")
        print("  python run_tui_tests.py --quick    # Fast unit tests")
        print("  make test-tui-unit                 # Unit tests via Make")
        print("  make test-tui                      # All TUI tests")
        print("\n📖 See tests/TUI_TESTING_GUIDE.md for comprehensive documentation")
        return 0
    else:
        print("❌ Some validation checks failed!")
        print("\n🔧 Fix the issues above and run this script again.")
        print("\n💡 Common fixes:")
        print("  uv sync --extra dev               # Install dependencies")
        print("  pip install pytest-textual-snapshot  # Install snapshot testing")
        return 1


if __name__ == '__main__':
    sys.exit(main())