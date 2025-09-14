"""
TUI Snapshot Tests for Visual Regression Detection.

This module uses pytest-textual-snapshot to capture and compare
visual representations of the TUI application for regression testing.
"""

import pytest
from textual.geometry import Size
from textual.widgets import TabbedContent

from mcp_vultr.tui_app import VultrTUI


@pytest.fixture
def tui_test_sizes():
    """Provide different terminal sizes for responsive testing."""
    return {
        "small": Size(60, 20),
        "standard": Size(100, 30), 
        "large": Size(120, 40),
        "wide": Size(150, 30),
        "tall": Size(100, 50)
    }


class TestTUISnapshots:
    """Visual regression tests using snapshot comparison."""

    @pytest.mark.tui_snapshot
    async def test_welcome_screen_snapshot(self, snap_compare):
        """Capture snapshot of welcome screen."""
        app = VultrTUI()
        async with app.run_test() as pilot:
            await pilot.pause(0.2)  # Allow rendering to complete
            assert snap_compare(app, "welcome_screen.txt")

    @pytest.mark.tui_snapshot
    async def test_mcp_setup_screen_snapshot(self, snap_compare):
        """Capture snapshot of MCP setup screen."""
        app = VultrTUI()
        async with app.run_test() as pilot:
            # Navigate to setup tab
            tabbed_content = app.query_one(TabbedContent)
            tabbed_content.active = "setup"
            await pilot.pause(0.2)
            assert snap_compare(app, "mcp_setup_screen.txt")

    @pytest.mark.tui_snapshot
    async def test_api_showcase_screen_snapshot(self, snap_compare):
        """Capture snapshot of API showcase screen."""
        app = VultrTUI()
        async with app.run_test() as pilot:
            # Navigate to showcase tab
            tabbed_content = app.query_one(TabbedContent)
            tabbed_content.active = "showcase"
            await pilot.pause(0.2)
            assert snap_compare(app, "api_showcase_screen.txt")

    @pytest.mark.tui_snapshot
    async def test_help_screen_snapshot(self, snap_compare):
        """Capture snapshot of help screen."""
        app = VultrTUI()
        async with app.run_test() as pilot:
            # Navigate to help tab
            tabbed_content = app.query_one(TabbedContent)
            tabbed_content.active = "help"
            await pilot.pause(0.2)
            assert snap_compare(app, "help_screen.txt")

    @pytest.mark.tui_snapshot
    async def test_small_terminal_responsive_snapshot(self, snap_compare, tui_test_sizes):
        """Test visual layout on small terminal."""
        app = VultrTUI()
        async with app.run_test(size=tui_test_sizes["small"]) as pilot:
            await pilot.pause(0.2)
            assert snap_compare(app, "small_terminal_layout.txt")

    @pytest.mark.tui_snapshot
    async def test_large_terminal_responsive_snapshot(self, snap_compare, tui_test_sizes):
        """Test visual layout on large terminal."""
        app = VultrTUI()
        async with app.run_test(size=tui_test_sizes["large"]) as pilot:
            await pilot.pause(0.2)
            assert snap_compare(app, "large_terminal_layout.txt")

    @pytest.mark.tui_snapshot
    async def test_wide_terminal_responsive_snapshot(self, snap_compare, tui_test_sizes):
        """Test visual layout on wide terminal."""
        app = VultrTUI()
        async with app.run_test(size=tui_test_sizes["wide"]) as pilot:
            await pilot.pause(0.2)
            assert snap_compare(app, "wide_terminal_layout.txt")

    @pytest.mark.tui_snapshot
    async def test_tab_navigation_sequence_snapshots(self, snap_compare):
        """Capture snapshots during tab navigation sequence."""
        app = VultrTUI()
        async with app.run_test() as pilot:
            tabbed_content = app.query_one(TabbedContent)
            
            # Capture each tab state
            tabs = [
                ("welcome", "nav_sequence_welcome.txt"),
                ("setup", "nav_sequence_setup.txt"), 
                ("showcase", "nav_sequence_showcase.txt"),
                ("help", "nav_sequence_help.txt")
            ]
            
            for tab_id, snapshot_name in tabs:
                tabbed_content.active = tab_id
                await pilot.pause(0.2)
                assert snap_compare(app, snapshot_name)

    @pytest.mark.tui_snapshot
    async def test_keyboard_shortcut_snapshots(self, snap_compare):
        """Test snapshots after keyboard shortcuts."""
        app = VultrTUI()
        async with app.run_test() as pilot:
            # Initial state
            await pilot.pause(0.1)
            assert snap_compare(app, "initial_state.txt")
            
            # After Ctrl+H (help)
            await pilot.press("ctrl+h")
            await pilot.pause(0.2)
            assert snap_compare(app, "after_ctrl_h.txt")
            
            # After Ctrl+S (setup)
            await pilot.press("ctrl+s")
            await pilot.pause(0.2)
            assert snap_compare(app, "after_ctrl_s.txt")

    @pytest.mark.tui_snapshot
    async def test_responsive_content_snapshots(self, snap_compare, tui_test_sizes):
        """Test content adaptation across different screen sizes."""
        for size_name, size in tui_test_sizes.items():
            app = VultrTUI()
            async with app.run_test(size=size) as pilot:
                # Test welcome screen at this size
                await pilot.pause(0.2)
                assert snap_compare(app, f"responsive_welcome_{size_name}.txt")
                
                # Test setup screen at this size
                tabbed_content = app.query_one(TabbedContent)
                tabbed_content.active = "setup"
                await pilot.pause(0.2)
                assert snap_compare(app, f"responsive_setup_{size_name}.txt")


class TestTUIThemeSnapshots:
    """Theme and styling snapshot tests."""

    @pytest.mark.tui_snapshot
    async def test_default_theme_consistency(self, snap_compare):
        """Test default theme appears consistently."""
        app = VultrTUI()
        async with app.run_test() as pilot:
            # Capture default theme on each screen
            screens = ["welcome", "setup", "showcase", "help"]
            tabbed_content = app.query_one(TabbedContent)
            
            for screen in screens:
                tabbed_content.active = screen
                await pilot.pause(0.2)
                assert snap_compare(app, f"theme_default_{screen}.txt")

    @pytest.mark.tui_snapshot
    async def test_header_footer_consistency(self, snap_compare):
        """Test header and footer remain consistent across screens."""
        app = VultrTUI()
        async with app.run_test() as pilot:
            # Test header/footer on different screens
            tabbed_content = app.query_one(TabbedContent)
            
            for tab_id in ["welcome", "setup", "showcase", "help"]:
                tabbed_content.active = tab_id
                await pilot.pause(0.2)
                assert snap_compare(app, f"header_footer_{tab_id}.txt")

    @pytest.mark.tui_snapshot
    async def test_tab_styling_consistency(self, snap_compare):
        """Test tab styling remains consistent."""
        app = VultrTUI()
        async with app.run_test() as pilot:
            await pilot.pause(0.2)
            
            # Focus on tab area specifically
            tabbed_content = app.query_one(TabbedContent)
            assert tabbed_content is not None
            
            # Capture tab styling in different states
            for tab_id in ["welcome", "setup", "showcase", "help"]:
                tabbed_content.active = tab_id
                await pilot.pause(0.1)
                assert snap_compare(app, f"tab_styling_{tab_id}_active.txt")


class TestTUIContentSnapshots:
    """Content-specific snapshot tests."""

    @pytest.mark.tui_snapshot
    async def test_welcome_content_structure(self, snap_compare):
        """Test welcome screen content structure."""
        app = VultrTUI()
        async with app.run_test() as pilot:
            await pilot.pause(0.2)
            
            # Verify welcome content structure is maintained
            assert snap_compare(app, "welcome_content_structure.txt")

    @pytest.mark.tui_snapshot
    async def test_mcp_setup_instructions(self, snap_compare):
        """Test MCP setup instructions formatting."""
        app = VultrTUI()
        async with app.run_test() as pilot:
            tabbed_content = app.query_one(TabbedContent)
            tabbed_content.active = "setup"
            await pilot.pause(0.2)
            
            # Verify setup instructions are properly formatted
            assert snap_compare(app, "mcp_setup_instructions.txt")

    @pytest.mark.tui_snapshot
    async def test_api_showcase_tree_structure(self, snap_compare):
        """Test API showcase tree structure."""
        app = VultrTUI()
        async with app.run_test() as pilot:
            tabbed_content = app.query_one(TabbedContent)
            tabbed_content.active = "showcase"
            await pilot.pause(0.2)
            
            # Verify tree structure is maintained
            assert snap_compare(app, "api_showcase_tree.txt")

    @pytest.mark.tui_snapshot
    async def test_help_documentation_formatting(self, snap_compare):
        """Test help documentation formatting."""
        app = VultrTUI()
        async with app.run_test() as pilot:
            tabbed_content = app.query_one(TabbedContent)
            tabbed_content.active = "help"
            await pilot.pause(0.2)
            
            # Verify help documentation formatting
            assert snap_compare(app, "help_documentation.txt")


class TestTUIInteractionSnapshots:
    """Interaction sequence snapshot tests."""

    @pytest.mark.tui_snapshot
    async def test_complete_user_journey_snapshots(self, snap_compare):
        """Test complete user journey through the application."""
        app = VultrTUI()
        async with app.run_test() as pilot:
            # Step 1: Initial load
            await pilot.pause(0.2)
            assert snap_compare(app, "journey_01_initial.txt")
            
            # Step 2: Explore MCP setup
            await pilot.press("ctrl+s")
            await pilot.pause(0.2)
            assert snap_compare(app, "journey_02_setup.txt")
            
            # Step 3: View API showcase
            tabbed_content = app.query_one(TabbedContent)
            tabbed_content.active = "showcase"
            await pilot.pause(0.2)
            assert snap_compare(app, "journey_03_showcase.txt")
            
            # Step 4: Check help
            await pilot.press("ctrl+h")
            await pilot.pause(0.2)
            assert snap_compare(app, "journey_04_help.txt")
            
            # Step 5: Return to welcome
            tabbed_content.active = "welcome"
            await pilot.pause(0.2)
            assert snap_compare(app, "journey_05_return.txt")

    @pytest.mark.tui_snapshot
    async def test_rapid_navigation_snapshots(self, snap_compare):
        """Test snapshots during rapid navigation."""
        app = VultrTUI()
        async with app.run_test() as pilot:
            tabbed_content = app.query_one(TabbedContent)
            
            # Rapid navigation sequence
            navigation_sequence = [
                ("welcome", "rapid_nav_welcome.txt"),
                ("setup", "rapid_nav_setup.txt"),
                ("showcase", "rapid_nav_showcase.txt"),
                ("help", "rapid_nav_help.txt"),
                ("welcome", "rapid_nav_return.txt")
            ]
            
            for tab_id, snapshot_name in navigation_sequence:
                tabbed_content.active = tab_id
                await pilot.pause(0.1)  # Shorter pause for rapid navigation
                assert snap_compare(app, snapshot_name)

    @pytest.mark.tui_snapshot
    async def test_accessibility_focus_snapshots(self, snap_compare):
        """Test visual focus states for accessibility."""
        app = VultrTUI()
        async with app.run_test() as pilot:
            # Test different focus states
            await pilot.pause(0.2)
            assert snap_compare(app, "focus_initial.txt")
            
            # Navigate with Tab key
            await pilot.press("tab")
            await pilot.pause(0.1)
            assert snap_compare(app, "focus_tab_navigation.txt")
            
            # Test keyboard shortcuts with focus
            await pilot.press("ctrl+h")
            await pilot.pause(0.2)
            assert snap_compare(app, "focus_help_active.txt")


class TestTUIEdgeCaseSnapshots:
    """Edge case and error state snapshots."""

    @pytest.mark.tui_snapshot
    async def test_minimum_terminal_size_snapshot(self, snap_compare):
        """Test appearance at minimum supported terminal size."""
        app = VultrTUI()
        min_size = Size(40, 15)  # Very small terminal
        
        async with app.run_test(size=min_size) as pilot:
            await pilot.pause(0.2)
            assert snap_compare(app, "minimum_terminal_size.txt")

    @pytest.mark.tui_snapshot
    async def test_maximum_terminal_size_snapshot(self, snap_compare):
        """Test appearance at very large terminal size."""
        app = VultrTUI()
        max_size = Size(200, 60)  # Very large terminal
        
        async with app.run_test(size=max_size) as pilot:
            await pilot.pause(0.2)
            assert snap_compare(app, "maximum_terminal_size.txt")

    @pytest.mark.tui_snapshot
    async def test_narrow_terminal_snapshot(self, snap_compare):
        """Test appearance on narrow terminal."""
        app = VultrTUI()
        narrow_size = Size(50, 30)  # Narrow but tall
        
        async with app.run_test(size=narrow_size) as pilot:
            await pilot.pause(0.2)
            assert snap_compare(app, "narrow_terminal.txt")

    @pytest.mark.tui_snapshot
    async def test_short_terminal_snapshot(self, snap_compare):
        """Test appearance on short terminal."""
        app = VultrTUI()
        short_size = Size(120, 15)  # Wide but short
        
        async with app.run_test(size=short_size) as pilot:
            await pilot.pause(0.2)
            assert snap_compare(app, "short_terminal.txt")