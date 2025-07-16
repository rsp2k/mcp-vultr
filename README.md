# Vultr DNS MCP

A comprehensive Model Context Protocol (MCP) server for managing Vultr DNS records through natural language interfaces.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

## Features

- **Complete MCP Server**: Full Model Context Protocol implementation with 12 tools and 3 resources
- **Comprehensive DNS Management**: Support for all major record types (A, AAAA, CNAME, MX, TXT, NS, SRV)
- **Intelligent Validation**: Pre-creation validation with helpful suggestions and warnings
- **Configuration Analysis**: DNS setup analysis with security recommendations
- **CLI Interface**: Complete command-line tool for direct DNS operations
- **High-Level Client**: Convenient Python API for common operations
- **Modern Development**: Fast development workflow with uv support

## Quick Start

### Installation

```bash
# Using uv (recommended - fast and modern)
uv add vultr-dns-mcp

# Or using pip
pip install vultr-dns-mcp
```

### Basic Usage

```bash
# Set your Vultr API key
export VULTR_API_KEY="your-api-key"

# List domains
vultr-dns-mcp domains list

# List DNS records
vultr-dns-mcp records list example.com

# Set up basic website DNS
vultr-dns-mcp setup-website example.com 192.168.1.100

# Run as MCP server
uv run python -m vultr_dns_mcp.server
```

### Python API

```python
import asyncio
from vultr_dns_mcp import VultrDNSClient

async def main():
    client = VultrDNSClient("your-api-key")
    
    # List domains
    domains = await client.domains()
    
    # Add DNS records
    await client.add_a_record("example.com", "www", "192.168.1.100")
    await client.add_mx_record("example.com", "@", "mail.example.com", 10)
    
    # Get domain summary
    summary = await client.get_domain_summary("example.com")
    print(f"Domain has {summary['total_records']} records")

asyncio.run(main())
```

### MCP Integration

This package provides a complete MCP server that can be integrated with MCP-compatible clients:

```python
from vultr_dns_mcp import create_mcp_server, run_server

# Create server
server = create_mcp_server("your-api-key")

# Run server
await run_server("your-api-key")
```

## Development

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Vultr API key

### Setup with uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/rsp2k/vultr-dns-mcp.git
cd vultr-dns-mcp

# Install dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Run comprehensive test suite
uv run python run_tests.py --all-checks

# Format code
uv run black src tests
uv run isort src tests

# Type checking
uv run mypy src
```

### Setup with pip (Traditional)

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .[dev]

# Run tests
pytest

# Run comprehensive test suite
python run_tests.py --all-checks
```

## MCP Tools Available

| Tool | Description |
|------|-------------|
| `list_dns_domains` | List all DNS domains |
| `get_dns_domain` | Get domain details |
| `create_dns_domain` | Create new domain |
| `delete_dns_domain` | Delete domain and all records |
| `list_dns_records` | List records for a domain |
| `get_dns_record` | Get specific record details |
| `create_dns_record` | Create new DNS record |
| `update_dns_record` | Update existing record |
| `delete_dns_record` | Delete DNS record |
| `validate_dns_record` | Validate record before creation |
| `analyze_dns_records` | Analyze domain configuration |

## CLI Commands

```bash
# Domain management
vultr-dns-mcp domains list
vultr-dns-mcp domains info example.com
vultr-dns-mcp domains create newdomain.com 192.168.1.100

# Record management
vultr-dns-mcp records list example.com
vultr-dns-mcp records add example.com A www 192.168.1.100
vultr-dns-mcp records delete example.com record-id

# Setup utilities
vultr-dns-mcp setup-website example.com 192.168.1.100
vultr-dns-mcp setup-email example.com mail.example.com

# Start MCP server
vultr-dns-mcp server
```

## Testing

This project follows FastMCP testing best practices with comprehensive test coverage:

```bash
# Run all tests (uv)
uv run pytest

# Run specific test categories
uv run pytest -m unit          # Unit tests
uv run pytest -m integration   # Integration tests  
uv run pytest -m mcp          # MCP-specific tests

# With coverage
uv run pytest --cov=vultr_dns_mcp --cov-report=html

# Full validation suite
uv run python run_tests.py --all-checks
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run the test suite (`uv run python run_tests.py --all-checks`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Error Handling

The package provides specific exception types for better error handling:

```python
from vultr_dns_mcp import (
    VultrAPIError,
    VultrAuthError,
    VultrRateLimitError,
    VultrResourceNotFoundError,
    VultrValidationError
)

try:
    await client.get_domain("example.com")
except VultrAuthError:
    print("Invalid API key or insufficient permissions")
except VultrResourceNotFoundError:
    print("Domain not found")
except VultrRateLimitError:
    print("Rate limit exceeded, please try again later")
except VultrAPIError as e:
    print(f"API error {e.status_code}: {e.message}")
```

## Configuration

Set your Vultr API key via environment variable:

```bash
export VULTR_API_KEY="your-vultr-api-key"
```

Or pass directly to the client:

```python
client = VultrDNSClient("your-api-key")
server = create_mcp_server("your-api-key")
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Links

- [GitHub Repository](https://github.com/rsp2k/vultr-dns-mcp)
- [PyPI Package](https://pypi.org/project/vultr-dns-mcp/)
- [Vultr API Documentation](https://www.vultr.com/api/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [uv Package Manager](https://docs.astral.sh/uv/)