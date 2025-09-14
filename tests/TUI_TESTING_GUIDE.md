# TUI Testing Framework Guide

## Overview

This guide provides comprehensive documentation for testing the Vultr TUI application built with Textual. The testing framework is designed to provide enterprise-grade testing capabilities while maintaining excellent developer experience.

## Architecture

### Test Structure

```
tests/
├── test_tui_app.py          # Main TUI application tests
├── test_tui_performance.py  # Performance and stress tests
├── test_tui_snapshots.py    # Visual regression testing
├── test_tui_conftest.py     # TUI-specific fixtures and configuration
├── snapshots/               # Visual snapshots for regression testing
└── TUI_TESTING_GUIDE.md     # This documentation
```

### Test Categories

#### 1. **Unit Tests** (`@pytest.mark.tui_unit`)
- Test individual widgets in isolation
- Fast execution (<5 seconds per test)
- Focus on widget composition and content verification
- Examples: WelcomeScreen content, APIShowcaseScreen tree structure

#### 2. **Integration Tests** (`@pytest.mark.tui_integration`)
- Test complete workflows and user interactions
- Tab navigation, keyboard shortcuts, app lifecycle
- Examples: Complete navigation workflow, keyboard navigation workflow

#### 3. **Snapshot Tests** (`@pytest.mark.tui_snapshot`)
- Visual regression testing using text-based snapshots
- Detect unintended visual changes
- Test responsive behavior at different screen sizes
- Examples: Full app snapshots, widget-specific snapshots

#### 4. **Performance Tests** (`@pytest.mark.tui_performance`)
- Ensure TUI remains responsive under load
- Test startup time, tab switching performance, memory usage
- Stress testing with rapid interactions
- Examples: Rapid tab switching, sustained operation testing

## Running Tests

### Quick Commands

```bash
# All TUI tests
make test-tui

# Specific categories
make test-tui-unit          # Widget unit tests
make test-tui-integration   # Workflow tests  
make test-tui-snapshots     # Visual regression tests
make test-tui-performance   # Performance tests

# Update visual snapshots
make test-tui-snapshots-update

# Responsive testing
make test-tui-responsive
```

### Direct pytest Commands

```bash
# All TUI tests
uv run pytest -m "tui"

# Unit tests only (fastest)
uv run pytest -m "tui_unit"

# Integration tests
uv run pytest -m "tui_integration"

# Snapshot tests
uv run pytest -m "tui_snapshot"

# Performance tests (may be slow)
uv run pytest -m "tui_performance"

# Run specific test file
uv run pytest tests/test_tui_app.py -v

# Run with coverage
uv run pytest -m "tui" --cov=mcp_vultr.tui_app
```

## Test Development Guidelines

### Writing Widget Unit Tests

```python
@pytest.mark.tui
@pytest.mark.tui_unit
@pytest.mark.fast
async def test_welcome_screen_composition(self):
    """Test welcome screen contains expected content."""
    app = App()
    
    async with app.run_test() as pilot:
        welcome = WelcomeScreen()
        await app.mount(welcome)
        await pilot.pause()
        
        # Check that markdown content is present
        markdown = welcome.query_one(Markdown)
        content = markdown.markdown
        
        # Verify key content elements
        assert "Welcome to Vultr Management TUI" in content
        assert "335+ management tools" in content
```

### Writing Integration Tests

```python
@pytest.mark.tui
@pytest.mark.tui_integration
async def test_complete_navigation_workflow(self):
    """Test complete navigation through all tabs."""
    app = VultrTUI()
    
    async with app.run_test() as pilot:
        tabbed_content = app.query_one(TabbedContent)
        
        # Test navigation to each tab
        tabs = ["welcome", "setup", "showcase", "help"]
        
        for tab_id in tabs:
            tabbed_content.active = tab_id
            await pilot.pause()
            
            assert tabbed_content.active == tab_id
            
            # Verify tab content is properly rendered
            active_pane = tabbed_content.get_pane(tab_id)
            assert active_pane is not None
            assert active_pane.is_mounted()
```

### Writing Snapshot Tests

```python
@pytest.mark.tui
@pytest.mark.tui_snapshot
async def test_full_app_welcome_snapshot(self, snap_compare, tui_test_size):
    """Test complete app appearance on welcome tab."""
    app = VultrTUI()
    
    async with app.run_test(size=tui_test_size) as pilot:
        await pilot.pause(0.2)  # Let app fully render
        
        # Take snapshot of complete app
        assert snap_compare(app, "full_app_welcome.txt")
```

### Writing Performance Tests

```python
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
        assert startup_time < 1.0, f"Startup took {startup_time:.2f}s"
```

## Best Practices

### Test Design

1. **Use Appropriate Markers**: Always mark tests with appropriate categories
2. **Keep Tests Focused**: Each test should verify one specific behavior
3. **Use Fixtures**: Leverage provided fixtures for consistent test setup
4. **Handle Async Properly**: Always use `async`/`await` patterns correctly
5. **Add Pauses**: Use `await pilot.pause()` to let UI elements render

### Performance Considerations

1. **Session-Scoped Fixtures**: Use session-scoped fixtures for expensive setup
2. **Minimal Pauses**: Use the shortest pause times that allow proper rendering
3. **Fast Tests First**: Mark fast tests appropriately for quick development cycles
4. **Parallel Execution**: Structure tests to support parallel execution

### Snapshot Testing

1. **Consistent Sizing**: Use standard test sizes for reproducible snapshots
2. **Update Snapshots**: Use `UPDATE_SNAPSHOTS=1` to update snapshots when UI changes
3. **Review Changes**: Always review snapshot changes before committing
4. **Multiple Sizes**: Test responsive behavior with different terminal sizes

## Configuration

### Fixtures Available

#### Standard Fixtures
- `tui_test_size`: Standard terminal size (100, 30)
- `large_tui_test_size`: Large terminal size (120, 40)  
- `small_tui_test_size`: Small terminal size (60, 20)
- `snap_compare`: Snapshot comparison function
- `tui_helper`: Helper utilities for common testing patterns

#### Advanced Fixtures
- `performance_monitor`: Performance metrics monitoring
- `widget_factory`: Factory for creating test widgets
- `keyboard_tester`: Keyboard interaction testing utilities

### Environment Variables

- `UPDATE_SNAPSHOTS=1`: Update visual snapshots instead of comparing
- `TEXTUAL_DISABLE_ANIMATIONS=1`: Disable animations for faster testing
- `TUI_TEST_MODE=1`: Enable test-specific behaviors

## Troubleshooting

### Common Issues

#### Test Timeouts
```bash
# Run with longer timeout
uv run pytest -m "tui" --timeout=60

# Debug specific hanging test
uv run pytest tests/test_tui_app.py::test_specific -v --timeout=30
```

#### Snapshot Mismatches
```bash
# Update snapshots after UI changes
UPDATE_SNAPSHOTS=1 uv run pytest -m "tui_snapshot"

# Compare specific snapshot
uv run pytest tests/test_tui_snapshots.py::test_specific_snapshot -v
```

#### Performance Issues
```bash
# Run performance tests with profiling
uv run pytest -m "tui_performance" --durations=10

# Memory profiling (requires memory_profiler)
mprof run uv run pytest -m "tui"
mprof plot
```

### Debugging Tests

#### Verbose Output
```bash
# Maximum verbosity
uv run pytest tests/test_tui_app.py -vvv

# Show test output
uv run pytest tests/test_tui_app.py -s
```

#### Test Discovery
```bash
# See what tests will run
uv run pytest --collect-only -m "tui"

# Validate test markers
uv run pytest --markers
```

## Integration with Existing Tests

### Test Execution Profiles

The TUI tests integrate seamlessly with existing test profiles:

```bash
# Fast development (excludes slow TUI performance tests)
make test-fast

# Full coverage including TUI
make test-coverage

# CI/CD pipeline
make test-ci
```

### Coverage Integration

TUI tests are included in coverage reporting:

```bash
# Coverage for TUI module specifically
uv run pytest -m "tui" --cov=mcp_vultr.tui_app --cov-report=html

# Full project coverage including TUI
make test-coverage
```

## Continuous Integration

### GitHub Actions Integration

TUI tests are automatically run in CI with appropriate timeouts and error handling:

```yaml
- name: Run TUI Tests
  run: |
    uv run pytest -m "tui and not slow" --timeout=30
    
- name: Run TUI Performance Tests
  run: |
    uv run pytest -m "tui_performance" --timeout=120
```

### Performance Monitoring

CI tracks TUI test performance to detect regressions:

- Startup time monitoring
- Tab switching performance
- Memory usage tracking
- Test execution duration

## Example Test Session

```bash
# 1. Install dependencies
make install-deps

# 2. Run quick TUI unit tests during development
make test-tui-unit

# 3. Run integration tests when ready
make test-tui-integration

# 4. Update snapshots after UI changes
make test-tui-snapshots-update

# 5. Run full TUI test suite before commit
make test-tui

# 6. Include TUI in full test suite
make test-coverage
```

## Performance Expectations

### Timing Targets

- **Unit Tests**: < 5 seconds each
- **Integration Tests**: < 10 seconds each  
- **Snapshot Tests**: < 5 seconds each
- **Performance Tests**: < 30 seconds each
- **Full TUI Suite**: < 2 minutes

### Resource Usage

- **Memory**: < 50MB increase during test suite
- **CPU**: < 20% average during idle testing
- **Startup Time**: < 1 second for app initialization

## Future Enhancements

### Planned Features

1. **Accessibility Testing**: Screen reader compatibility tests
2. **Theme Testing**: Multiple color scheme validation
3. **Interaction Recording**: Playback of user interaction sequences
4. **Load Testing**: Stress testing with large datasets
5. **Cross-Platform Testing**: Validation across different terminal emulators

### Contributing

When adding new TUI functionality:

1. **Add Unit Tests**: For new widgets and components
2. **Add Integration Tests**: For new workflows and interactions
3. **Update Snapshots**: If visual changes are expected
4. **Add Performance Tests**: If changes could affect performance
5. **Update Documentation**: Keep this guide current

## Support

For questions about TUI testing:

1. **Check Examples**: Look at existing test files for patterns
2. **Review Textual Docs**: [Textual testing documentation](https://textual.textualize.io/guide/testing/)
3. **Run Test Validation**: `make test-validate` to check configuration
4. **Create Issues**: Use GitHub issues for bugs or feature requests

---

*This testing framework ensures the Vultr TUI application maintains enterprise-grade quality while providing an excellent developer experience.*