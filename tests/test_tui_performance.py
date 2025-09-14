"""
Performance and stress tests for the Vultr TUI application.

This module provides comprehensive performance testing to ensure
the TUI remains responsive under various load conditions.
"""

import pytest
import time
import asyncio
from unittest.mock import patch

from mcp_vultr.tui_app import VultrTUI, APIShowcaseScreen, WelcomeScreen


class TestTUIPerformance:
    """Performance tests for TUI application."""

    @pytest.mark.tui
    @pytest.mark.tui_performance
    @pytest.mark.timeout_sensitive
    async def test_app_startup_time(self):
        """Test that app starts up within acceptable time limits."""
        start_time = time.time()
        
        app = VultrTUI()
        
        async with app.run_test() as pilot:
            await pilot.pause()  # Let app fully initialize
            
            end_time = time.time()
            startup_time = end_time - start_time
            
            # Should start up in under 1 second
            assert startup_time < 1.0, f"Startup took {startup_time:.2f}s, expected < 1.0s"

    @pytest.mark.tui
    @pytest.mark.tui_performance
    async def test_tab_switching_performance(self):
        """Test performance of rapid tab switching."""
        app = VultrTUI()
        
        async with app.run_test() as pilot:
            tabbed_content = app.query_one("TabbedContent")
            tabs = ["welcome", "setup", "showcase", "help"]
            
            # Warm up - switch to each tab once
            for tab_id in tabs:
                tabbed_content.active = tab_id
                await pilot.pause(0.1)
            
            # Performance test - rapid switching
            start_time = time.time()
            
            for _ in range(20):  # 20 rapid switches
                for tab_id in tabs:
                    tabbed_content.active = tab_id
                    await pilot.pause(0.01)  # Minimal pause
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Should complete 80 tab switches in under 5 seconds
            assert total_time < 5.0, f"Tab switching took {total_time:.2f}s, expected < 5.0s"
            
            # Calculate average time per switch
            avg_time = total_time / 80
            assert avg_time < 0.05, f"Average switch time {avg_time:.3f}s, expected < 0.05s"

    @pytest.mark.tui
    @pytest.mark.tui_performance
    async def test_tree_rendering_performance(self):
        """Test performance of tree widget rendering in API showcase."""
        start_time = time.time()
        
        app = VultrTUI()
        
        async with app.run_test() as pilot:
            # Navigate to showcase tab
            tabbed_content = app.query_one("TabbedContent")
            tabbed_content.active = "showcase"
            await pilot.pause()
            
            # Tree should be rendered quickly
            tree = app.query_one("Tree")
            assert tree is not None
            
            end_time = time.time()
            render_time = end_time - start_time
            
            # Tree rendering should be fast
            assert render_time < 2.0, f"Tree rendering took {render_time:.2f}s, expected < 2.0s"

    @pytest.mark.tui
    @pytest.mark.tui_performance
    async def test_markdown_rendering_performance(self):
        """Test performance of markdown content rendering."""
        app = VultrTUI()
        
        async with app.run_test() as pilot:
            tabs_with_markdown = ["welcome", "setup", "help"]
            
            for tab_id in tabs_with_markdown:
                start_time = time.time()
                
                tabbed_content = app.query_one("TabbedContent")
                tabbed_content.active = tab_id
                await pilot.pause()
                
                # Markdown should be rendered
                markdown = app.query_one("Markdown")
                assert markdown is not None
                
                end_time = time.time()
                render_time = end_time - start_time
                
                # Each markdown tab should render quickly
                assert render_time < 1.0, f"Markdown in {tab_id} took {render_time:.2f}s"

    @pytest.mark.tui
    @pytest.mark.tui_performance
    async def test_keyboard_input_responsiveness(self):
        """Test responsiveness to keyboard input under load."""
        app = VultrTUI()
        
        async with app.run_test() as pilot:
            # Simulate rapid keyboard input
            start_time = time.time()
            
            shortcuts = ["ctrl+s", "ctrl+h", "ctrl+s", "ctrl+h"]
            
            for _ in range(10):  # 10 cycles of shortcuts
                for shortcut in shortcuts:
                    await pilot.press(shortcut)
                    await pilot.pause(0.01)  # Very short pause
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Should handle 40 keyboard inputs in under 3 seconds
            assert total_time < 3.0, f"Keyboard input handling took {total_time:.2f}s"
            
            # App should still be responsive
            assert app.is_running
            
            # Final navigation should work
            await pilot.press("ctrl+h")
            await pilot.pause()
            tabbed_content = app.query_one("TabbedContent")
            assert tabbed_content.active == "help"

    @pytest.mark.tui
    @pytest.mark.tui_performance
    async def test_memory_usage_stability(self):
        """Test that memory usage remains stable during extended use."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        app = VultrTUI()
        
        async with app.run_test() as pilot:
            tabbed_content = app.query_one("TabbedContent")
            tabs = ["welcome", "setup", "showcase", "help"]
            
            # Simulate extended usage
            for cycle in range(50):  # 50 cycles of tab switching
                for tab_id in tabs:
                    tabbed_content.active = tab_id
                    await pilot.pause(0.01)
                
                # Check memory every 10 cycles
                if cycle % 10 == 0:
                    current_memory = process.memory_info().rss
                    memory_increase = current_memory - initial_memory
                    
                    # Memory increase should be reasonable (< 50MB)
                    assert memory_increase < 50 * 1024 * 1024, f"Memory increased by {memory_increase / 1024 / 1024:.1f}MB"

    @pytest.mark.tui
    @pytest.mark.tui_performance
    @pytest.mark.slow
    async def test_sustained_operation(self):
        """Test TUI performance during sustained operation."""
        app = VultrTUI()
        
        async with app.run_test() as pilot:
            start_time = time.time()
            
            # Run for extended period with various interactions
            end_time = start_time + 30  # Run for 30 seconds
            
            while time.time() < end_time:
                # Mix of different operations
                await pilot.press("ctrl+s")
                await pilot.pause(0.1)
                
                await pilot.press("ctrl+h")
                await pilot.pause(0.1)
                
                # Manual tab switching
                tabbed_content = app.query_one("TabbedContent")
                tabbed_content.active = "showcase"
                await pilot.pause(0.1)
                
                tabbed_content.active = "welcome"
                await pilot.pause(0.1)
                
                # Brief rest
                await pilot.pause(0.5)
            
            # App should still be responsive after sustained use
            assert app.is_running
            
            # Test final interaction
            await pilot.press("ctrl+h")
            await pilot.pause()
            tabbed_content = app.query_one("TabbedContent")
            assert tabbed_content.active == "help"


class TestTUIStressTesting:
    """Stress tests for TUI application."""

    @pytest.mark.tui
    @pytest.mark.tui_performance
    @pytest.mark.slow
    async def test_rapid_resize_handling(self):
        """Test handling of rapid terminal size changes."""
        # Note: This test simulates resize events rather than actual resizing
        # as pytest-textual doesn't support dynamic resizing during tests
        
        app = VultrTUI()
        
        # Test with various sizes
        sizes = [(80, 24), (120, 40), (60, 20), (100, 30)]
        
        for width, height in sizes:
            async with app.run_test(size=(width, height)) as pilot:
                await pilot.pause()
                
                # App should render correctly at each size
                assert app.is_running
                
                # Basic functionality should work
                tabbed_content = app.query_one("TabbedContent")
                tabbed_content.active = "showcase"
                await pilot.pause()
                assert tabbed_content.active == "showcase"

    @pytest.mark.tui
    @pytest.mark.tui_performance
    async def test_concurrent_widget_updates(self):
        """Test handling of concurrent widget updates."""
        app = VultrTUI()
        
        async with app.run_test() as pilot:
            tabbed_content = app.query_one("TabbedContent")
            
            # Simulate concurrent updates
            async def rapid_navigation():
                for i in range(20):
                    tabs = ["welcome", "setup", "showcase", "help"]
                    tabbed_content.active = tabs[i % 4]
                    await asyncio.sleep(0.01)
            
            # Run multiple navigation tasks concurrently
            tasks = [rapid_navigation() for _ in range(3)]
            
            start_time = time.time()
            await asyncio.gather(*tasks)
            end_time = time.time()
            
            total_time = end_time - start_time
            
            # Should handle concurrent updates without performance degradation
            assert total_time < 5.0, f"Concurrent updates took {total_time:.2f}s"
            
            # App should still be functional
            assert app.is_running
            await pilot.press("ctrl+h")
            await pilot.pause()
            assert tabbed_content.active == "help"

    @pytest.mark.tui
    @pytest.mark.tui_performance
    async def test_large_content_handling(self):
        """Test performance with large content in widgets."""
        # Test by creating a widget with artificially large content
        from textual.app import App
        from textual.widgets import Markdown
        
        # Create large markdown content
        large_content = "\n".join([f"# Section {i}\n\nContent for section {i}" for i in range(1000)])
        
        app = App()
        
        async with app.run_test() as pilot:
            start_time = time.time()
            
            markdown = Markdown(large_content)
            await app.mount(markdown)
            await pilot.pause()
            
            end_time = time.time()
            render_time = end_time - start_time
            
            # Should handle large content reasonably well
            assert render_time < 5.0, f"Large content rendering took {render_time:.2f}s"


class TestTUIResourceUsage:
    """Test resource usage patterns of the TUI."""

    @pytest.mark.tui
    @pytest.mark.tui_performance
    async def test_cpu_usage_efficiency(self):
        """Test that TUI doesn't consume excessive CPU."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        app = VultrTUI()
        
        async with app.run_test() as pilot:
            # Let app settle
            await pilot.pause(1.0)
            
            # Measure CPU usage during idle state
            cpu_samples = []
            for _ in range(10):
                cpu_percent = process.cpu_percent(interval=0.1)
                cpu_samples.append(cpu_percent)
                await pilot.pause(0.1)
            
            # During idle, CPU usage should be low
            avg_cpu = sum(cpu_samples) / len(cpu_samples)
            assert avg_cpu < 20.0, f"Average CPU usage {avg_cpu:.1f}%, expected < 20%"

    @pytest.mark.tui
    @pytest.mark.tui_performance
    async def test_event_loop_efficiency(self):
        """Test that the event loop remains efficient."""
        app = VultrTUI()
        
        async with app.run_test() as pilot:
            start_time = time.time()
            
            # Perform various operations
            operations = 0
            while time.time() - start_time < 2.0:  # Run for 2 seconds
                await pilot.press("ctrl+s")
                await pilot.pause(0.01)
                operations += 1
            
            # Should be able to perform many operations in 2 seconds
            operations_per_second = operations / 2.0
            assert operations_per_second > 50, f"Only {operations_per_second:.1f} ops/sec, expected > 50"

    @pytest.mark.tui
    @pytest.mark.tui_performance
    async def test_widget_lifecycle_efficiency(self):
        """Test that widget creation and destruction is efficient."""
        from textual.app import App
        from textual.widgets import Static
        
        app = App()
        
        async with app.run_test() as pilot:
            start_time = time.time()
            
            # Create and destroy many widgets
            for i in range(100):
                widget = Static(f"Test widget {i}")
                await app.mount(widget)
                await pilot.pause(0.001)
                widget.remove()
                await pilot.pause(0.001)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Should handle widget lifecycle efficiently
            assert total_time < 5.0, f"Widget lifecycle took {total_time:.2f}s for 100 widgets"


if __name__ == "__main__":
    # Run performance tests only
    pytest.main([__file__, "-m", "tui_performance", "-v"])