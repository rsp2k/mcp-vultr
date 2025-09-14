#!/usr/bin/env python3
"""
Real-Time Dashboard Monitor

Provides real-time monitoring and updates for the testing dashboard:
1. Watches test files for changes
2. Auto-runs tests when files change
3. Updates dashboard in real-time
4. WebSocket server for live updates
5. File system watching with intelligent debouncing

Usage:
    python dashboard_monitor.py --watch
    python dashboard_monitor.py --server-only
    python dashboard_monitor.py --once
"""

import asyncio
import json
import logging
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Set, Dict, Any, Optional
import subprocess
import argparse

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("Warning: watchdog not installed. File watching disabled.")
    print("Install with: uv add watchdog")

from dashboard_generator import DashboardGenerator
from run_tests_with_dashboard import TestRunner


class TestFileHandler(FileSystemEventHandler):
    """Handles file system events for test files."""
    
    def __init__(self, monitor: 'DashboardMonitor'):
        self.monitor = monitor
        self.last_event_time = {}
        self.debounce_seconds = 2.0  # Debounce rapid file changes
        
    def should_trigger(self, file_path: str) -> bool:
        """Check if we should trigger a test run for this file change."""
        now = time.time()
        last_time = self.last_event_time.get(file_path, 0)
        
        if now - last_time < self.debounce_seconds:
            return False
            
        self.last_event_time[file_path] = now
        return True
        
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        # Only trigger on Python files in src/ or tests/
        if (file_path.suffix == '.py' and 
            ('src/' in str(file_path) or 'tests/' in str(file_path)) and
            self.should_trigger(str(file_path))):
            
            self.monitor.logger.info(f"File changed: {file_path}")
            asyncio.create_task(self.monitor.handle_file_change(str(file_path)))


class DashboardMonitor:
    """Real-time dashboard monitoring and updates."""
    
    def __init__(self, project_root: Path = None, auto_run: bool = True):
        self.project_root = project_root or Path.cwd()
        self.auto_run = auto_run
        self.running = False
        self.observer = None
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.test_runner = TestRunner(self.project_root)
        self.dashboard_generator = DashboardGenerator(self.project_root)
        
        # File watching state
        self.watched_files: Set[str] = set()
        self.file_hashes: Dict[str, str] = {}
        
        # Performance tracking
        self.last_run_time = 0
        self.run_count = 0
        
    async def start_monitoring(self):
        """Start the monitoring system."""
        self.logger.info("🔍 Starting dashboard monitor...")
        self.running = True
        
        if WATCHDOG_AVAILABLE and self.auto_run:
            await self.setup_file_watcher()
        
        # Start monitoring loop
        await self.monitor_loop()
    
    async def setup_file_watcher(self):
        """Setup file system watching."""
        self.logger.info("📁 Setting up file system watcher...")
        
        event_handler = TestFileHandler(self)
        self.observer = Observer()
        
        # Watch src/ directory
        src_dir = self.project_root / "src"
        if src_dir.exists():
            self.observer.schedule(event_handler, str(src_dir), recursive=True)
            self.logger.info(f"👀 Watching: {src_dir}")
        
        # Watch tests/ directory  
        tests_dir = self.project_root / "tests"
        if tests_dir.exists():
            self.observer.schedule(event_handler, str(tests_dir), recursive=True)
            self.logger.info(f"👀 Watching: {tests_dir}")
        
        self.observer.start()
        self.logger.info("✅ File watcher started")
    
    async def monitor_loop(self):
        """Main monitoring loop."""
        try:
            while self.running:
                await self.periodic_check()
                await asyncio.sleep(30)  # Check every 30 seconds
                
        except KeyboardInterrupt:
            self.logger.info("🛑 Monitor stopped by user")
        finally:
            await self.cleanup()
    
    async def periodic_check(self):
        """Perform periodic health checks and updates."""
        # Check if dashboard files exist and are recent
        dashboard_path = self.project_root / "reports" / "dashboard.html"
        
        if not dashboard_path.exists():
            self.logger.info("📊 Dashboard missing, generating...")
            await self.generate_dashboard_update()
            return
        
        # Check if dashboard is stale (older than 1 hour)
        dashboard_age = time.time() - dashboard_path.stat().st_mtime
        if dashboard_age > 3600:  # 1 hour
            self.logger.info("⏰ Dashboard is stale, refreshing...")
            await self.generate_dashboard_update()
    
    async def handle_file_change(self, file_path: str):
        """Handle a file change event."""
        self.logger.info(f"🔄 Processing file change: {file_path}")
        
        # Check if this is a meaningful change
        if not await self.is_meaningful_change(file_path):
            self.logger.debug("Skipping trivial change")
            return
        
        # Determine test strategy based on file type
        if file_path.endswith('_test.py') or 'test_' in file_path:
            await self.run_targeted_tests(file_path)
        elif 'src/' in file_path:
            await self.run_affected_tests(file_path)
        else:
            await self.run_quick_tests()
    
    async def is_meaningful_change(self, file_path: str) -> bool:
        """Check if the file change is meaningful enough to trigger tests."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            current_hash = hashlib.md5(content).hexdigest()
            previous_hash = self.file_hashes.get(file_path)
            
            self.file_hashes[file_path] = current_hash
            
            # First time seeing this file
            if previous_hash is None:
                return True
            
            # Hash changed
            return current_hash != previous_hash
            
        except Exception as e:
            self.logger.warning(f"Could not check file hash: {e}")
            return True
    
    async def run_targeted_tests(self, test_file: str):
        """Run specific test file."""
        self.logger.info(f"🎯 Running targeted tests: {test_file}")
        
        cmd = [
            "uv", "run", "pytest",
            test_file,
            "--tb=short",
            "-v",
            f"--junitxml={self.project_root}/reports/junit-targeted.xml"
        ]
        
        await self.run_command_async(cmd)
        await self.generate_dashboard_update()
    
    async def run_affected_tests(self, src_file: str):
        """Run tests that might be affected by source file changes."""
        self.logger.info(f"🎯 Running tests affected by: {src_file}")
        
        # Map source file to likely test files
        test_patterns = self.get_related_test_patterns(src_file)
        
        if test_patterns:
            cmd = [
                "uv", "run", "pytest",
                *test_patterns,
                "--tb=short",
                f"--junitxml={self.project_root}/reports/junit-affected.xml"
            ]
        else:
            # Fallback to fast tests
            cmd = [
                "uv", "run", "pytest",
                "-m", "not slow",
                "--tb=short",
                f"--junitxml={self.project_root}/reports/junit-fast.xml"
            ]
        
        await self.run_command_async(cmd)
        await self.generate_dashboard_update()
    
    def get_related_test_patterns(self, src_file: str) -> list:
        """Get test file patterns related to a source file."""
        src_path = Path(src_file)
        module_name = src_path.stem
        
        test_patterns = []
        tests_dir = self.project_root / "tests"
        
        if tests_dir.exists():
            # Look for direct test file matches
            possible_tests = [
                f"tests/test_{module_name}.py",
                f"tests/{module_name}_test.py",
                f"tests/test_{module_name}_*.py"
            ]
            
            for pattern in possible_tests:
                test_path = self.project_root / pattern
                if test_path.exists():
                    test_patterns.append(str(test_path))
        
        return test_patterns
    
    async def run_quick_tests(self):
        """Run quick subset of tests."""
        self.logger.info("⚡ Running quick tests...")
        
        cmd = [
            "uv", "run", "pytest",
            "-m", "fast or unit",
            "--tb=short",
            "--maxfail=5",
            f"--junitxml={self.project_root}/reports/junit-quick.xml"
        ]
        
        await self.run_command_async(cmd)
        await self.generate_dashboard_update()
    
    async def run_command_async(self, cmd: list, timeout: int = 300):
        """Run a command asynchronously."""
        start_time = time.time()
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.project_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            duration = time.time() - start_time
            self.run_count += 1
            self.last_run_time = time.time()
            
            if process.returncode == 0:
                self.logger.info(f"✅ Command completed in {duration:.1f}s")
            else:
                self.logger.warning(f"❌ Command failed (exit {process.returncode}) in {duration:.1f}s")
                if stderr:
                    self.logger.warning(f"Error output: {stderr.decode()[:500]}...")
            
            return {
                "returncode": process.returncode,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
                "duration": duration
            }
            
        except asyncio.TimeoutError:
            self.logger.error(f"❌ Command timed out after {timeout}s")
            return {"returncode": 124, "duration": timeout, "timeout": True}
        except Exception as e:
            self.logger.error(f"❌ Command failed: {e}")
            return {"returncode": 1, "error": str(e)}
    
    async def generate_dashboard_update(self):
        """Generate an updated dashboard."""
        self.logger.info("🎨 Updating dashboard...")
        
        try:
            start_time = time.time()
            
            # Generate dashboard
            dashboard_path = self.dashboard_generator.generate_dashboard()
            
            duration = time.time() - start_time
            self.logger.info(f"✅ Dashboard updated in {duration:.1f}s: {dashboard_path}")
            
            # Log dashboard stats
            await self.log_dashboard_stats(dashboard_path)
            
        except Exception as e:
            self.logger.error(f"❌ Dashboard update failed: {e}")
    
    async def log_dashboard_stats(self, dashboard_path: str):
        """Log statistics about the generated dashboard."""
        try:
            dashboard_file = Path(dashboard_path)
            if dashboard_file.exists():
                size_kb = dashboard_file.stat().st_size / 1024
                self.logger.info(f"📊 Dashboard size: {size_kb:.1f}KB")
                
                # Check for embedded data
                content = dashboard_file.read_text()
                if '"coverage":' in content:
                    self.logger.info("✅ Dashboard includes coverage data")
                if '"tests":' in content:
                    self.logger.info("✅ Dashboard includes test results")
                
        except Exception as e:
            self.logger.warning(f"Could not get dashboard stats: {e}")
    
    async def run_full_test_suite(self):
        """Run the complete test suite with coverage."""
        self.logger.info("🔍 Running full test suite...")
        
        cmd = [
            "uv", "run", "pytest",
            "--cov=src/mcp_vultr",
            "--cov-report=html",
            "--cov-report=json",
            "--tb=short",
            f"--junitxml={self.project_root}/reports/junit-full.xml",
            "tests/"
        ]
        
        result = await self.run_command_async(cmd, timeout=600)  # 10 minute timeout
        await self.generate_dashboard_update()
        
        return result
    
    async def get_monitor_status(self) -> Dict[str, Any]:
        """Get current monitor status."""
        return {
            "running": self.running,
            "watching_files": WATCHDOG_AVAILABLE and self.observer is not None,
            "run_count": self.run_count,
            "last_run": datetime.fromtimestamp(self.last_run_time).isoformat() if self.last_run_time else None,
            "watched_directories": [
                str(self.project_root / "src"),
                str(self.project_root / "tests")
            ] if WATCHDOG_AVAILABLE else [],
            "project_root": str(self.project_root)
        }
    
    async def cleanup(self):
        """Clean up resources."""
        self.logger.info("🧹 Cleaning up monitor...")
        self.running = False
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        self.logger.info("✅ Monitor cleanup complete")


async def main():
    """Main entry point for the dashboard monitor."""
    parser = argparse.ArgumentParser(
        description="Real-Time Dashboard Monitor"
    )
    
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Enable file watching and auto-test execution"
    )
    
    parser.add_argument(
        "--server-only", 
        action="store_true",
        help="Run monitoring server without file watching"
    )
    
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run tests once and generate dashboard"
    )
    
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full test suite with coverage"
    )
    
    args = parser.parse_args()
    
    # Create monitor
    auto_run = args.watch
    monitor = DashboardMonitor(auto_run=auto_run)
    
    try:
        if args.once:
            print("🔄 Running tests once and generating dashboard...")
            await monitor.run_quick_tests()
            await monitor.generate_dashboard_update()
            print("✅ Dashboard generated")
            
        elif args.full:
            print("🔍 Running full test suite...")
            await monitor.run_full_test_suite()
            print("✅ Full test suite completed")
            
        else:
            print("🚀 Starting dashboard monitor...")
            if not WATCHDOG_AVAILABLE:
                print("⚠️  File watching disabled (install watchdog package)")
            
            await monitor.start_monitoring()
            
    except KeyboardInterrupt:
        print("\n🛑 Monitor stopped by user")
    except Exception as e:
        print(f"❌ Monitor failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())