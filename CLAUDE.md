# Vultr DNS MCP Package

A Model Context Protocol (MCP) server for managing Vultr DNS domains and records through natural language interfaces.

## Project Overview

This package provides both an MCP server and a standalone Python client for Vultr DNS management. It supports all major DNS record types (A, AAAA, CNAME, MX, TXT, NS, SRV) with validation, analysis, and batch operations.

## Quick Start

### Installation
```bash
# Using uv (recommended)
uv add vultr-dns-mcp

# Or using pip
pip install vultr-dns-mcp
```

### Basic Usage
```bash
# CLI - requires VULTR_API_KEY environment variable
vultr-dns-mcp domains list
vultr-dns-mcp records list example.com

# As MCP server
uv run python -m vultr_dns_mcp.server --api-key YOUR_API_KEY
```

## Development Setup

### Dependencies
```bash
# Using uv (recommended)
uv sync --extra dev

# Or using pip
pip install -e .[dev]
```

### Running Tests
```bash
# All tests (using uv - recommended)
uv run pytest

# Specific categories
uv run pytest -m unit
uv run pytest -m mcp
uv run pytest -m integration

# With coverage
uv run pytest --cov=vultr_dns_mcp --cov-report=html

# Comprehensive test runner
uv run python run_tests.py --all-checks

# Traditional approach (fallback)
pytest
```

### Code Quality
```bash
# Using uv (recommended)
uv run black src tests
uv run isort src tests
uv run mypy src
uv run flake8 src tests

# Traditional approach
black src tests
isort src tests
mypy src
flake8 src tests
```

### Build & Publishing
```bash
# Using uv (recommended)
uv build
uv run twine check dist/*
uv run twine upload --repository testpypi dist/*
uv run twine upload dist/*

# Traditional approach
python -m build
python -m twine check dist/*
python -m twine upload --repository testpypi dist/*
python -m twine upload dist/*
```

## Test Structure

Following FastMCP testing best practices:

- `tests/conftest.py` - Test configuration and fixtures
- `tests/test_mcp_server.py` - MCP server functionality tests using in-memory pattern
- `tests/test_client.py` - VultrDNSClient tests  
- `tests/test_cli.py` - CLI interface tests
- `tests/test_vultr_server.py` - Core VultrDNSServer tests
- `tests/test_package_validation.py` - Package integrity tests

### Test Markers
- `@pytest.mark.unit` - Individual component testing
- `@pytest.mark.integration` - Component interaction testing  
- `@pytest.mark.mcp` - MCP-specific functionality
- `@pytest.mark.slow` - Performance and timeout tests

### Coverage Goals
- Overall: 80%+ (enforced)
- MCP Tools: 100% (critical functionality)
- API Client: 95%+ (core functionality)
- CLI Commands: 90%+ (user interface)

## Project Structure

```
vultr-dns-mcp/
├── src/vultr_dns_mcp/
│   ├── client.py           # High-level DNS client
│   ├── server.py           # Core Vultr API client
│   ├── mcp_server.py       # MCP server implementation
│   └── cli.py              # Command-line interface
├── tests/                  # Comprehensive test suite
├── docs/                   # Documentation
└── pyproject.toml          # Project configuration
```

## Key Features

### MCP Tools (12 total)
- Domain management: list, create, delete, get details
- DNS record operations: CRUD for all record types
- Validation: Pre-creation validation with suggestions
- Analysis: Configuration analysis with security recommendations

### MCP Resources
- Domain discovery endpoints
- DNS record resources
- Configuration capabilities

### CLI Commands
- Domain operations: `domains list|create|delete|get`
- Record operations: `records list|create|update|delete`
- Setup utilities: `setup website|email`

## Version History

### Current: 1.0.1
- Fixed FastMCP server initialization
- Corrected MCP server creation for current FastMCP version
- Simplified initialization to use only name parameter

### 1.0.0 - Initial Release
- Complete MCP server implementation
- Python client library
- CLI interface
- Support for all DNS record types
- Validation and analysis features
- Comprehensive test suite

## CI/CD Pipeline

### GitHub Actions
- Multi-Python testing (3.8-3.12)
- Progressive test execution: validation → unit → integration → mcp
- Code quality gates: black, isort, flake8, mypy
- Security scanning: safety, bandit
- Package validation: build, install, test CLI

### Quality Gates
1. All tests pass on all Python versions
2. Code coverage meets 80% threshold  
3. Code quality checks pass
4. Security scans clean
5. Package builds and installs correctly

## Publishing

### Automated (Recommended)
1. Update version in `pyproject.toml`
2. Commit and push changes
3. Create and push version tag: `git tag v1.0.2 && git push origin v1.0.2`
4. Workflow automatically publishes to PyPI

### Manual
Use the GitHub Actions "Publish to PyPI" workflow with manual trigger.

## Development Guidelines

### Testing
- Use FastMCP in-memory testing pattern for MCP functionality
- Mock external dependencies (Vultr API)
- Maintain high coverage on critical paths
- Follow pytest best practices

### Code Style
- Black formatting
- isort import sorting
- Type hints with mypy
- Comprehensive docstrings
- Security best practices

### Release Process
1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Run full test suite
4. Create git tag
5. Automated publishing via GitHub Actions

## Troubleshooting

### Common Issues
- **ImportError**: Run `pip install -e .` from repository root
- **AsyncioError**: Ensure `asyncio_mode = "auto"` in pyproject.toml
- **MockError**: Check that test fixtures are properly configured
- **API Errors**: Verify VULTR_API_KEY environment variable

### Test Debugging
```bash
# Single test with verbose output (using uv)
uv run pytest tests/test_mcp_server.py::TestMCPTools::test_list_dns_domains_tool -vvv

# Check pytest configuration
uv run pytest --collect-only tests/

# Validate imports
uv run python -c "from vultr_dns_mcp.server import create_mcp_server"

# Traditional approach
pytest tests/test_mcp_server.py::TestMCPTools::test_list_dns_domains_tool -vvv
pytest --collect-only tests/
python -c "from vultr_dns_mcp.server import create_mcp_server"
```

## Support & Documentation

- **GitHub**: https://github.com/rsp2k/vultr-dns-mcp
- **PyPI**: https://pypi.org/project/vultr-dns-mcp/
- **Documentation**: Complete API documentation and examples in package
- **Issues**: Use GitHub Issues for bug reports and feature requests