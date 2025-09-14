"""
TUI-specific test configuration and fixtures.

This module provides specialized fixtures and configuration
for Textual TUI testing with snapshot support.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch

from textual.app import App
from textual.pilot import Pilot


# Snapshot testing configuration
@pytest.fixture(scope="session")
def snap_compare(request):
    """
    Fixture for snapshot testing with pytest-textual-snapshot.
    
    Creates a comparison function for TUI visual regression testing.
    """
    def compare(app_or_widget, snapshot_name: str) -> bool:
        """Compare current app/widget state with snapshot."""
        # Get the test file directory for storing snapshots
        test_dir = Path(request.fspath).parent
        snapshots_dir = test_dir / "snapshots"
        snapshots_dir.mkdir(exist_ok=True)
        
        snapshot_path = snapshots_dir / snapshot_name
        
        # Get the current rendered output
        if hasattr(app_or_widget, 'export_text'):
            current_output = app_or_widget.export_text()
        else:
            # For App instances, we need to get the screen content
            current_output = str(app_or_widget.screen)
        
        # If snapshot doesn't exist, create it
        if not snapshot_path.exists():
            snapshot_path.write_text(current_output, encoding='utf-8')
            return True
        
        # Compare with existing snapshot
        expected_output = snapshot_path.read_text(encoding='utf-8')
        
        if current_output.strip() == expected_output.strip():
            return True
        
        # If running in update mode, update the snapshot
        if os.environ.get('UPDATE_SNAPSHOTS') == '1':
            snapshot_path.write_text(current_output, encoding='utf-8')
            return True
        
        # Show diff for debugging
        print(f"\nSnapshot mismatch for {snapshot_name}")
        print(f"Expected length: {len(expected_output)}")
        print(f"Actual length: {len(current_output)}")
        
        return False
    
    return compare


@pytest.fixture
def tui_test_size():
    """Standard terminal size for TUI tests."""
    return (100, 30)


@pytest.fixture
def large_tui_test_size():
    """Large terminal size for comprehensive TUI tests."""
    return (120, 40)


@pytest.fixture
def small_tui_test_size():
    """Small terminal size for responsive TUI tests."""
    return (60, 20)


@pytest.fixture
async def tui_app():
    """
    Create a TUI app instance for testing.
    
    Provides a clean app instance that's properly initialized
    but not yet running.
    """
    from mcp_vultr.tui_app import VultrTUI
    
    app = VultrTUI()
    
    # Apply any test-specific configuration
    # For example, disable animations for faster testing
    app.animation_level = "none"
    
    yield app
    
    # Cleanup
    if app.is_running:
        app.exit()


@pytest.fixture
async def running_tui_app(tui_app, tui_test_size):
    """
    Create a running TUI app instance for testing.
    
    Provides an app that's already running within a test context.
    """
    async with tui_app.run_test(size=tui_test_size) as pilot:
        # Let the app fully initialize
        await pilot.pause(0.1)
        yield tui_app, pilot


@pytest.fixture
def mock_version():
    """Mock version for consistent testing."""
    with patch('mcp_vultr.tui_app.__version__', '2.1.0-test'):
        yield '2.1.0-test'


@pytest.fixture
def tui_test_environment(monkeypatch):
    """
    Set up a clean test environment for TUI tests.
    
    Configures environment variables and mocks for consistent testing.
    """
    # Set test environment variables
    monkeypatch.setenv('VULTR_API_KEY', 'test-key-123')
    monkeypatch.setenv('TUI_TEST_MODE', '1')
    
    # Mock any external dependencies that could affect TUI rendering
    with patch('mcp_vultr.tui_app.time.time', return_value=1640995200.0):  # Fixed timestamp
        yield


@pytest.fixture
def performance_monitor():
    """
    Monitor performance metrics during TUI tests.
    
    Provides utilities for measuring timing and resource usage.
    """
    import time
    import psutil
    import os
    
    class PerformanceMonitor:
        def __init__(self):
            self.process = psutil.Process(os.getpid())
            self.start_time = None
            self.start_memory = None
            self.start_cpu = None
        
        def start(self):
            """Start monitoring performance."""
            self.start_time = time.time()
            self.start_memory = self.process.memory_info().rss
            self.start_cpu = self.process.cpu_percent()
        
        def stop(self):
            """Stop monitoring and return metrics."""
            if self.start_time is None:
                raise ValueError("Performance monitoring not started")
            
            end_time = time.time()
            end_memory = self.process.memory_info().rss
            end_cpu = self.process.cpu_percent()
            
            return {
                'duration': end_time - self.start_time,
                'memory_delta': end_memory - self.start_memory,
                'cpu_avg': (self.start_cpu + end_cpu) / 2,
                'memory_peak': end_memory
            }
        
        def assert_performance(self, max_duration=None, max_memory_mb=None, max_cpu=None):
            """Assert performance metrics are within acceptable ranges."""
            metrics = self.stop()
            
            if max_duration and metrics['duration'] > max_duration:
                pytest.fail(f"Operation took {metrics['duration']:.2f}s, expected < {max_duration}s")
            
            if max_memory_mb:
                memory_mb = metrics['memory_delta'] / (1024 * 1024)
                if memory_mb > max_memory_mb:
                    pytest.fail(f"Memory increased by {memory_mb:.1f}MB, expected < {max_memory_mb}MB")
            
            if max_cpu and metrics['cpu_avg'] > max_cpu:
                pytest.fail(f"CPU usage averaged {metrics['cpu_avg']:.1f}%, expected < {max_cpu}%")
    
    return PerformanceMonitor()


@pytest.fixture
def widget_factory():
    """
    Factory for creating TUI widgets for testing.
    
    Provides a convenient way to create and configure widgets
    for isolated testing.
    """
    class WidgetFactory:
        def __init__(self):
            self.created_widgets = []
        
        def create_welcome_screen(self):
            """Create a WelcomeScreen widget for testing."""
            from mcp_vultr.tui_app import WelcomeScreen
            widget = WelcomeScreen()
            self.created_widgets.append(widget)
            return widget
        
        def create_mcp_setup_screen(self):
            """Create an MCPSetupScreen widget for testing."""
            from mcp_vultr.tui_app import MCPSetupScreen
            widget = MCPSetupScreen()
            self.created_widgets.append(widget)
            return widget
        
        def create_api_showcase_screen(self):
            """Create an APIShowcaseScreen widget for testing."""
            from mcp_vultr.tui_app import APIShowcaseScreen
            widget = APIShowcaseScreen()
            self.created_widgets.append(widget)
            return widget
        
        def create_help_screen(self):
            """Create a HelpScreen widget for testing."""
            from mcp_vultr.tui_app import HelpScreen
            widget = HelpScreen()
            self.created_widgets.append(widget)
            return widget
        
        def cleanup(self):
            """Clean up created widgets."""
            for widget in self.created_widgets:
                if hasattr(widget, 'remove'):
                    try:
                        widget.remove()
                    except Exception:
                        pass  # Widget might already be removed
            self.created_widgets.clear()
    
    factory = WidgetFactory()
    yield factory
    factory.cleanup()


@pytest.fixture
def keyboard_tester():
    """
    Utility for testing keyboard interactions.
    
    Provides helpers for simulating complex keyboard sequences
    and verifying their effects.
    """
    class KeyboardTester:
        def __init__(self):
            self.key_sequence = []
        
        async def press_sequence(self, pilot: Pilot, keys: list, pause_between=0.01):
            """Press a sequence of keys with optional pauses."""
            for key in keys:
                await pilot.press(key)
                self.key_sequence.append(key)
                if pause_between:
                    await pilot.pause(pause_between)
        
        async def press_shortcuts(self, pilot: Pilot, shortcuts: list):
            """Press a series of keyboard shortcuts."""
            for shortcut in shortcuts:
                await pilot.press(shortcut)
                self.key_sequence.append(shortcut)
                await pilot.pause(0.05)  # Small pause between shortcuts
        
        def get_sequence(self):
            """Get the recorded key sequence."""
            return self.key_sequence.copy()
        
        def clear_sequence(self):
            """Clear the recorded key sequence."""
            self.key_sequence.clear()
    
    return KeyboardTester()


@pytest.fixture(autouse=True)
def configure_tui_testing():
    """
    Auto-applied fixture to configure the environment for TUI testing.
    
    Sets up optimal conditions for TUI tests including:
    - Disabling animations for speed
    - Setting consistent terminal settings
    - Configuring snapshot directories
    """
    # Set environment variables for consistent TUI testing
    os.environ['TEXTUAL_DISABLE_ANIMATIONS'] = '1'
    os.environ['TEXTUAL_LOG_LEVEL'] = 'WARNING'
    
    yield
    
    # Cleanup
    if 'TEXTUAL_DISABLE_ANIMATIONS' in os.environ:
        del os.environ['TEXTUAL_DISABLE_ANIMATIONS']
    if 'TEXTUAL_LOG_LEVEL' in os.environ:
        del os.environ['TEXTUAL_LOG_LEVEL']


# Custom markers for TUI tests
def pytest_configure(config):
    """Configure TUI-specific pytest markers."""
    # Add TUI-specific markers
    tui_markers = [
        "tui: TUI application tests",
        "tui_unit: TUI unit tests for individual widgets",
        "tui_integration: TUI integration tests for workflows",
        "tui_snapshot: TUI snapshot tests for visual regression",
        "tui_performance: TUI performance and responsiveness tests",
        "tui_accessibility: TUI accessibility and keyboard navigation tests",
        "tui_stress: TUI stress tests for edge cases"
    ]
    
    for marker in tui_markers:
        config.addinivalue_line("markers", marker)


def pytest_collection_modifyitems(config, items):
    """Modify test collection for TUI-specific optimizations."""
    for item in items:
        # Auto-mark TUI tests based on file patterns
        if "test_tui" in str(item.fspath):
            item.add_marker(pytest.mark.tui)
        
        # Mark performance tests as slow
        if "performance" in item.name.lower() or "stress" in item.name.lower():
            item.add_marker(pytest.mark.slow)
        
        # Mark snapshot tests
        if "snapshot" in item.name.lower() or "visual" in item.name.lower():
            item.add_marker(pytest.mark.tui_snapshot)


class TUITestHelper:
    """
    Helper class with common TUI testing utilities.
    
    Provides reusable methods for common TUI testing patterns.
    """
    
    @staticmethod
    async def navigate_to_tab(app, tab_id: str, pilot: Pilot):
        """Navigate to a specific tab and wait for it to load."""
        tabbed_content = app.query_one("TabbedContent")
        tabbed_content.active = tab_id
        await pilot.pause(0.1)  # Allow tab to fully load
        return tabbed_content
    
    @staticmethod
    async def verify_tab_content(app, tab_id: str, expected_widgets: list):
        """Verify that a tab contains expected widgets."""
        tabbed_content = app.query_one("TabbedContent")
        pane = tabbed_content.get_pane(tab_id)
        
        for widget_type in expected_widgets:
            widgets = pane.query(widget_type)
            assert len(widgets) > 0, f"Expected {widget_type} not found in {tab_id} tab"
    
    @staticmethod
    async def test_keyboard_shortcut(app, pilot: Pilot, shortcut: str, expected_tab: str):
        """Test a keyboard shortcut and verify the expected result."""
        await pilot.press(shortcut)
        await pilot.pause(0.1)
        
        tabbed_content = app.query_one("TabbedContent")
        assert tabbed_content.active == expected_tab, f"Shortcut {shortcut} should navigate to {expected_tab}"
    
    @staticmethod
    def assert_widget_exists(app, widget_selector: str, description: str = ""):
        """Assert that a widget exists in the app."""
        widgets = app.query(widget_selector)
        assert len(widgets) > 0, f"Widget {widget_selector} not found. {description}"
    
    @staticmethod
    def assert_widget_count(app, widget_selector: str, expected_count: int):
        """Assert that exactly the expected number of widgets exist."""
        widgets = app.query(widget_selector)
        actual_count = len(widgets)
        assert actual_count == expected_count, f"Expected {expected_count} {widget_selector} widgets, found {actual_count}"


# Make helper available as fixture
@pytest.fixture
def tui_helper():
    """Provide TUI testing helper utilities."""
    return TUITestHelper()