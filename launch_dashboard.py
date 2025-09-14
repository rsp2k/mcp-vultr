#!/usr/bin/env python3
"""
🎨 MCP-Vultr Dashboard Launcher

Simple launcher script that provides easy access to all dashboard functionality.
Perfect for getting started quickly with the testing dashboard system.

Usage:
    python launch_dashboard.py                    # Interactive menu
    python launch_dashboard.py --demo            # Generate demo dashboard
    python launch_dashboard.py --test            # Run tests + dashboard
    python launch_dashboard.py --monitor         # Start file monitoring
    python launch_dashboard.py --fix-coverage    # Fix coverage config only
"""

import argparse
import asyncio
import subprocess
import sys
import webbrowser
from pathlib import Path

from dashboard_generator import DashboardGenerator
from run_tests_with_dashboard import TestRunner
from dashboard_monitor import DashboardMonitor
from demo_dashboard import DemoDashboardGenerator


class DashboardLauncher:
    """Simple launcher for all dashboard functionality."""
    
    def __init__(self):
        self.project_root = Path.cwd()
        print("🎨 MCP-Vultr Testing Dashboard Launcher")
        print("="*50)
    
    def show_menu(self):
        """Show interactive menu."""
        print("\nWhat would you like to do?\n")
        
        options = [
            ("1", "🎨 Generate Demo Dashboard", "Create interactive demo with sample data"),
            ("2", "🧪 Run Tests + Dashboard", "Fix coverage, run tests, generate dashboard"),
            ("3", "👀 Start File Monitor", "Watch files and auto-update dashboard"),
            ("4", "📊 Dashboard Only", "Generate dashboard from existing results"),
            ("5", "🔧 Fix Coverage Config", "Fix coverage configuration only"),
            ("6", "⚡ Quick Tests", "Run fast tests without coverage"),
            ("7", "📈 Full Test Suite", "Run comprehensive tests with coverage"),
            ("8", "ℹ️  Show Status", "Show current project status"),
            ("q", "🚪 Quit", "Exit launcher")
        ]
        
        for option, title, description in options:
            print(f"  {option}) {title}")
            print(f"     {description}")
            print()
        
        choice = input("Enter your choice (1-8 or q): ").strip().lower()
        return choice
    
    def run_interactive(self):
        """Run interactive menu loop."""
        while True:
            try:
                choice = self.show_menu()
                
                if choice == 'q' or choice == 'quit':
                    print("👋 Goodbye!")
                    break
                elif choice == '1':
                    self.generate_demo()
                elif choice == '2':
                    self.run_tests_with_dashboard()
                elif choice == '3':
                    asyncio.run(self.start_monitor())
                elif choice == '4':
                    self.generate_dashboard_only()
                elif choice == '5':
                    self.fix_coverage_only()
                elif choice == '6':
                    self.run_quick_tests()
                elif choice == '7':
                    self.run_full_tests()
                elif choice == '8':
                    self.show_status()
                else:
                    print(f"❌ Invalid choice: {choice}")
                
                if choice != 'q':
                    input("\\nPress Enter to continue...")
                    print("\\n" + "="*50)
                    
            except KeyboardInterrupt:
                print("\\n👋 Interrupted by user")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                input("Press Enter to continue...")
    
    def generate_demo(self):
        """Generate interactive demo dashboard."""
        print("🎨 Generating demo dashboard...")
        
        try:
            demo_generator = DemoDashboardGenerator()
            dashboard_path = demo_generator.generate_demo_dashboard()
            
            print(f"✅ Demo dashboard generated: {dashboard_path}")
            
            # Ask to open in browser
            response = input("\\n🌐 Open in browser? (y/n): ").strip().lower()
            if response in ['y', 'yes', '']:
                webbrowser.open(f"file://{Path(dashboard_path).absolute()}")
                print("✅ Demo opened in browser")
                
        except Exception as e:
            print(f"❌ Demo generation failed: {e}")
    
    def run_tests_with_dashboard(self):
        """Run tests and generate dashboard."""
        print("🧪 Running tests with dashboard generation...")
        
        try:
            runner = TestRunner()
            results = runner.run_comprehensive_tests("all")
            
            # Generate dashboard
            dashboard_path = runner.generate_dashboard(results)
            
            print(f"\\n✅ Tests completed and dashboard generated: {dashboard_path}")
            
            # Show summary
            runner.print_summary(results)
            
            # Ask to open in browser
            response = input("\\n🌐 Open dashboard in browser? (y/n): ").strip().lower()
            if response in ['y', 'yes', '']:
                webbrowser.open(f"file://{Path(dashboard_path).absolute()}")
                print("✅ Dashboard opened in browser")
                
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
    
    async def start_monitor(self):
        """Start file monitoring system."""
        print("👀 Starting file monitor...")
        
        try:
            monitor = DashboardMonitor(auto_run=True)
            await monitor.start_monitoring()
        except Exception as e:
            print(f"❌ Monitor failed: {e}")
    
    def generate_dashboard_only(self):
        """Generate dashboard from existing results."""
        print("📊 Generating dashboard from existing results...")
        
        try:
            generator = DashboardGenerator()
            dashboard_path = generator.generate_dashboard()
            
            print(f"✅ Dashboard generated: {dashboard_path}")
            
            # Ask to open in browser
            response = input("\\n🌐 Open dashboard in browser? (y/n): ").strip().lower()
            if response in ['y', 'yes', '']:
                webbrowser.open(f"file://{Path(dashboard_path).absolute()}")
                print("✅ Dashboard opened in browser")
                
        except Exception as e:
            print(f"❌ Dashboard generation failed: {e}")
    
    def fix_coverage_only(self):
        """Fix coverage configuration only."""
        print("🔧 Fixing coverage configuration...")
        
        try:
            runner = TestRunner()
            coveragerc_path = runner.fix_coverage_configuration()
            
            print(f"✅ Coverage configuration fixed: {coveragerc_path}")
            print("\\n📋 Coverage settings:")
            print("   • Source directory: src/mcp_vultr")
            print("   • Omit test files and cache")
            print("   • Show missing lines")
            print("   • HTML report with contexts")
            
        except Exception as e:
            print(f"❌ Coverage fix failed: {e}")
    
    def run_quick_tests(self):
        """Run quick tests without coverage."""
        print("⚡ Running quick tests...")
        
        try:
            runner = TestRunner()
            results = runner.run_comprehensive_tests("fast")
            
            print("\\n✅ Quick tests completed")
            runner.print_summary(results)
            
        except Exception as e:
            print(f"❌ Quick tests failed: {e}")
    
    def run_full_tests(self):
        """Run full test suite with coverage."""
        print("📈 Running full test suite...")
        
        try:
            runner = TestRunner()
            results = runner.run_comprehensive_tests("all")
            
            # Generate dashboard
            dashboard_path = runner.generate_dashboard(results)
            
            print("\\n✅ Full test suite completed")
            runner.print_summary(results)
            
            print(f"📊 Dashboard: {dashboard_path}")
            
        except Exception as e:
            print(f"❌ Full test suite failed: {e}")
    
    def show_status(self):
        """Show current project status."""
        print("ℹ️  Project Status\\n")
        
        # Check if dashboard files exist
        reports_dir = self.project_root / "reports"
        dashboard_path = reports_dir / "dashboard.html"
        demo_path = reports_dir / "demo_dashboard.html"
        
        print(f"📁 Project Root: {self.project_root}")
        print(f"📁 Reports Dir: {reports_dir} ({'exists' if reports_dir.exists() else 'missing'})")
        
        if dashboard_path.exists():
            print(f"📊 Dashboard: {dashboard_path} ✅")
            print(f"   Last modified: {dashboard_path.stat().st_mtime}")
        else:
            print("📊 Dashboard: Missing ❌")
        
        if demo_path.exists():
            print(f"🎨 Demo: {demo_path} ✅")
        else:
            print("🎨 Demo: Missing ❌")
        
        # Check for coverage files
        coverage_files = list(self.project_root.glob("coverage.*"))
        print(f"📋 Coverage Files: {len(coverage_files)} found")
        for cov_file in coverage_files[:3]:  # Show first 3
            print(f"   {cov_file.name}")
        
        # Check for test results
        junit_files = list(reports_dir.glob("junit-*.xml")) if reports_dir.exists() else []
        print(f"🧪 Test Results: {len(junit_files)} files")
        
        # Check htmlcov directory
        htmlcov_dir = self.project_root / "htmlcov"
        if htmlcov_dir.exists():
            html_files = list(htmlcov_dir.glob("*.html"))
            print(f"📄 HTML Coverage: {len(html_files)} files")
        else:
            print("📄 HTML Coverage: Missing")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="🎨 MCP-Vultr Testing Dashboard Launcher"
    )
    
    parser.add_argument("--demo", action="store_true", help="Generate demo dashboard")
    parser.add_argument("--test", action="store_true", help="Run tests + dashboard") 
    parser.add_argument("--monitor", action="store_true", help="Start file monitoring")
    parser.add_argument("--dashboard", action="store_true", help="Generate dashboard only")
    parser.add_argument("--fix-coverage", action="store_true", help="Fix coverage config only")
    parser.add_argument("--quick", action="store_true", help="Run quick tests")
    parser.add_argument("--full", action="store_true", help="Run full test suite")
    parser.add_argument("--status", action="store_true", help="Show project status")
    
    args = parser.parse_args()
    
    launcher = DashboardLauncher()
    
    try:
        if args.demo:
            launcher.generate_demo()
        elif args.test:
            launcher.run_tests_with_dashboard()
        elif args.monitor:
            asyncio.run(launcher.start_monitor())
        elif args.dashboard:
            launcher.generate_dashboard_only()
        elif args.fix_coverage:
            launcher.fix_coverage_only()
        elif args.quick:
            launcher.run_quick_tests()
        elif args.full:
            launcher.run_full_tests()
        elif args.status:
            launcher.show_status()
        else:
            # Interactive mode
            launcher.run_interactive()
    
    except KeyboardInterrupt:
        print("\\n👋 Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\\n❌ Launcher failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()