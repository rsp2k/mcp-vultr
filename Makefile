# Makefile for mcp-vultr test execution optimization
# Provides different test execution profiles for performance optimization

.PHONY: help test test-fast test-coverage test-parallel test-unit test-integration test-mcp test-error test-slow test-tui test-tui-unit test-tui-integration test-tui-snapshots test-tui-performance install-deps clean

# Default target
help:
	@echo "Test execution profiles for performance optimization:"
	@echo ""
	@echo "Fast Development:"
	@echo "  make test-fast      - Quick tests without coverage (fastest)"
	@echo "  make test-unit      - Unit tests only"
	@echo "  make test-parallel  - Parallel execution (requires pytest-xdist)"
	@echo ""
	@echo "Comprehensive Testing:"
	@echo "  make test           - Standard test run with basic options"
	@echo "  make test-coverage  - Full test suite with coverage reporting"
	@echo "  make test-ci        - CI/CD optimized test run"
	@echo ""
	@echo "Targeted Testing:"
	@echo "  make test-integration - Integration tests only"
	@echo "  make test-mcp       - MCP server tests only"
	@echo "  make test-error     - Error handling tests only"
	@echo "  make test-slow      - Slow tests only (for debugging)"
	@echo ""
	@echo "TUI Testing:"
	@echo "  make test-tui       - All TUI tests"
	@echo "  make test-tui-unit  - TUI unit tests (individual widgets)"
	@echo "  make test-tui-integration - TUI integration tests (workflows)"
	@echo "  make test-tui-snapshots - TUI snapshot tests (visual regression)"
	@echo "  make test-tui-performance - TUI performance tests"
	@echo ""
	@echo "Maintenance:"
	@echo "  make install-deps   - Install test dependencies"
	@echo "  make clean          - Clean test artifacts"
	@echo "  make optimize       - Run test optimization scripts"

# Install test dependencies
install-deps:
	uv sync --extra dev
	@echo "✓ Test dependencies installed"

# Clean test artifacts
clean:
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf junit.xml
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.pyc" -delete
	@echo "✓ Test artifacts cleaned"

# Fast test execution (no coverage, minimal output)
test-fast:
	@echo "Running fast tests (no coverage)..."
	uv run pytest -m "not slow" --no-cov --tb=no -q --maxfail=3

# Unit tests only (fastest subset)
test-unit:
	@echo "Running unit tests..."
	uv run pytest -m "unit" --no-cov --tb=short -q

# Parallel test execution
test-parallel:
	@echo "Running tests in parallel..."
	uv run pytest -n auto -m "not slow" --tb=short

# Standard test run (balanced performance/coverage)
test:
	@echo "Running standard test suite..."
	uv run pytest --tb=short --maxfail=5

# Full coverage testing (slowest but most comprehensive)  
test-coverage:
	@echo "Running tests with full coverage..."
	uv run pytest --cov=mcp_vultr --cov-report=term-missing --cov-report=html --cov-fail-under=80

# CI/CD optimized test run
test-ci:
	@echo "Running CI optimized tests..."
	uv run pytest --cov=mcp_vultr --cov-report=xml --cov-report=term --cov-fail-under=80 --tb=short --maxfail=1 --junit-xml=junit.xml

# Integration tests
test-integration:
	@echo "Running integration tests..."
	uv run pytest -m "integration" --tb=short

# MCP server tests
test-mcp:
	@echo "Running MCP server tests..."
	uv run pytest -m "mcp" --tb=short

# Error handling tests
test-error:
	@echo "Running error handling tests..."
	uv run pytest -m "error_handling" --tb=long --timeout=60

# Slow tests (for debugging performance issues)
test-slow:
	@echo "Running slow tests..."
	uv run pytest -m "slow" --tb=long --timeout=120 -v

# Run all tests except slow ones
test-exclude-slow:
	@echo "Running all tests except slow ones..."
	uv run pytest -m "not slow" --tb=short

# Performance profiling test run
test-profile:
	@echo "Running tests with performance profiling..."
	uv run pytest --durations=10 --tb=no -q

# Stress test (run multiple times to find flaky tests)
test-stress:
	@echo "Running stress tests (5 iterations)..."
	for i in {1..5}; do \
		echo "Iteration $$i:"; \
		uv run pytest -x --tb=no -q || exit 1; \
	done
	@echo "✓ All stress test iterations passed"

# Run optimization scripts
optimize:
	@echo "Running test optimization scripts..."
	python optimize_error_tests.py
	@echo "✓ Test optimization complete"

# Debug hanging tests
test-debug-hangs:
	@echo "Running tests with detailed timeout debugging..."
	uv run pytest --timeout=30 --timeout-method=thread --tb=long -v -s

# Memory usage profiling (requires memory_profiler)
test-memory:
	@echo "Running tests with memory profiling..."
	@command -v mprof >/dev/null 2>&1 || { echo "Install memory_profiler: pip install memory_profiler"; exit 1; }
	mprof run uv run pytest -m "not slow" --tb=no -q
	mprof plot

# Run specific test file quickly
test-file:
	@if [ -z "$(FILE)" ]; then echo "Usage: make test-file FILE=tests/test_example.py"; exit 1; fi
	@echo "Running $(FILE)..."
	uv run pytest $(FILE) --tb=short -v

# Test performance comparison (before/after optimization)
test-benchmark:
	@echo "Running benchmark comparison..."
	@echo "Fast mode:"
	@time make test-fast
	@echo ""
	@echo "Standard mode:"
	@time make test
	@echo ""
	@echo "Parallel mode:"
	@time make test-parallel

# Validate test configuration
test-validate:
	@echo "Validating test configuration..."
	uv run pytest --collect-only -q
	@echo "✓ Test discovery successful"
	uv run pytest --markers
	@echo "✓ Test markers validated"

# TUI Tests
test-tui:
	@echo "Running all TUI tests..."
	uv run pytest -m "tui" --tb=short

test-tui-unit:
	@echo "Running TUI unit tests..."
	uv run pytest -m "tui_unit" --tb=short

test-tui-integration:
	@echo "Running TUI integration tests..."
	uv run pytest -m "tui_integration" --tb=short

test-tui-snapshots:
	@echo "Running TUI snapshot tests..."
	uv run pytest -m "tui_snapshot" --tb=short

test-tui-performance:
	@echo "Running TUI performance tests..."
	uv run pytest -m "tui_performance" --tb=short --timeout=60

# Update TUI snapshots
test-tui-snapshots-update:
	@echo "Updating TUI snapshots..."
	UPDATE_SNAPSHOTS=1 uv run pytest -m "tui_snapshot" --tb=short

# Run TUI tests with different terminal sizes
test-tui-responsive:
	@echo "Running TUI responsive tests..."
	uv run pytest tests/test_tui_snapshots.py::TestResponsiveSnapshots --tb=short

# Generate test execution report
test-report:
	@echo "Generating comprehensive test report..."
	uv run pytest --cov=mcp_vultr --cov-report=html --cov-report=term --junit-xml=junit.xml --html=report.html --self-contained-html
	@echo "✓ Test report generated: htmlcov/index.html, report.html"