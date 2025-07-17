# Vultr MCP

A comprehensive Model Context Protocol (MCP) server for managing Vultr services through natural language interfaces.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

## Features

- **Complete MCP Server**: Full Model Context Protocol implementation with 70+ tools across 8 service modules
- **Comprehensive Service Coverage**: 
  - **DNS Management**: Full DNS record management (A, AAAA, CNAME, MX, TXT, NS, SRV)
  - **Instance Management**: Create, manage, and control compute instances
  - **SSH Keys**: Manage SSH keys for secure access
  - **Backups**: Create and manage instance backups
  - **Firewall**: Configure firewall groups and rules
  - **Snapshots**: Create and manage instance snapshots
  - **Regions**: Query region availability and capabilities
  - **Reserved IPs**: Manage static IP addresses
- **Smart Identifier Resolution**: Use human-readable names instead of UUIDs (e.g., "web-server" instead of UUID)
- **Zone File Import/Export**: Standard zone file format support for bulk DNS operations
- **Intelligent Validation**: Pre-creation validation with helpful suggestions
- **CLI Interface**: Complete command-line tool for direct operations
- **High-Level Client**: Convenient Python API for common operations
- **Modern Development**: Fast development workflow with uv support

## Smart Identifier Resolution

One of the key features is **automatic UUID lookup** across all services. Instead of requiring UUIDs, you can use human-readable identifiers:

- **Instances**: Use label or hostname instead of UUID
- **SSH Keys**: Use key name instead of UUID  
- **Firewall Groups**: Use description instead of UUID
- **Snapshots**: Use description instead of UUID
- **Reserved IPs**: Use IP address instead of UUID

### Examples

```bash
# Traditional approach (with UUIDs)
mcp-vultr instances stop cb676a46-66fd-4dfb-b839-443f2e6c0b60
mcp-vultr firewall rules list 5f2a4b6c-7b8d-4e9f-a1b2-3c4d5e6f7a8b

# Smart approach (with names)
mcp-vultr instances stop web-server
mcp-vultr firewall rules list production-servers
```

The system uses **exact matching** to ensure safety - if multiple resources have similar names, you'll get an error rather than operating on the wrong resource.

## Quick Start

### Installation

```bash
# Using uv (recommended - fast and modern)
uv add mcp-vultr

# Or using pip
pip install mcp-vultr
```

### Basic Usage

```bash
# Set your Vultr API key
export VULTR_API_KEY="your-api-key"

# DNS Management
mcp-vultr domains list
mcp-vultr records list example.com
mcp-vultr setup-website example.com 192.168.1.100

# Instance Management (with smart name resolution)
mcp-vultr instances list
mcp-vultr instances get web-server  # Uses name instead of UUID
mcp-vultr instances stop web-server

# SSH Key Management
mcp-vultr ssh-keys list
mcp-vultr ssh-keys add "laptop" "ssh-rsa AAAAB3..."

# Firewall Management
mcp-vultr firewall groups list
mcp-vultr firewall rules list web-servers  # Uses description instead of UUID

# Run as MCP server
vultr-mcp-server
```

### Python API

```python
import asyncio
from mcp_vultr import VultrDNSClient, VultrDNSServer

async def main():
    # DNS-specific client
    dns_client = VultrDNSClient("your-api-key")
    
    # List domains
    domains = await dns_client.domains()
    
    # Add DNS records
    await dns_client.add_a_record("example.com", "www", "192.168.1.100")
    await dns_client.add_mx_record("example.com", "@", "mail.example.com", 10)
    
    # Get domain summary
    summary = await dns_client.get_domain_summary("example.com")
    print(f"Domain has {summary['total_records']} records")
    
    # Full API client for all services
    vultr = VultrDNSServer("your-api-key")
    
    # Smart identifier resolution - use names instead of UUIDs!
    instance = await vultr.get_instance("web-server")  # By label
    ssh_key = await vultr.get_ssh_key("laptop-key")   # By name
    firewall = await vultr.get_firewall_group("production")  # By description
    snapshot = await vultr.get_snapshot("backup-2024-01")    # By description
    reserved_ip = await vultr.get_reserved_ip("192.168.1.100")  # By IP

asyncio.run(main())
```

### MCP Integration

This package provides a complete MCP server that can be integrated with MCP-compatible clients:

```python
from mcp_vultr import create_mcp_server, run_server

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
git clone https://github.com/rsp2k/mcp-vultr.git
cd mcp-vultr

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

The MCP server provides 70+ tools across 8 service modules. All tools support **smart identifier resolution** - you can use human-readable names instead of UUIDs!

### DNS Management (12 tools)
- `dns_list_domains` - List all DNS domains
- `dns_get_domain` - Get domain details
- `dns_create_domain` - Create new domain
- `dns_delete_domain` - Delete domain and all records
- `dns_list_records` - List records for a domain
- `dns_create_record` - Create new DNS record
- `dns_update_record` - Update existing record
- `dns_delete_record` - Delete DNS record
- `dns_validate_record` - Validate record before creation
- `dns_analyze_records` - Analyze domain configuration
- `dns_import_zone_file` - Import DNS records from zone file
- `dns_export_zone_file` - Export DNS records to zone file

### Instance Management (9 tools)
- `instances_list` - List all instances
- `instances_get` - Get instance details (**smart**: by label, hostname, or UUID)
- `instances_create` - Create new instance
- `instances_update` - Update instance configuration
- `instances_delete` - Delete instance (**smart**: by label, hostname, or UUID)
- `instances_start` - Start a stopped instance (**smart**: by label, hostname, or UUID)
- `instances_stop` - Stop a running instance (**smart**: by label, hostname, or UUID)
- `instances_reboot` - Reboot instance (**smart**: by label, hostname, or UUID)
- `instances_reinstall` - Reinstall instance OS (**smart**: by label, hostname, or UUID)

### SSH Key Management (5 tools)
- `ssh_keys_list` - List all SSH keys
- `ssh_keys_get` - Get SSH key details (**smart**: by name or UUID)
- `ssh_keys_create` - Add new SSH key
- `ssh_keys_update` - Update SSH key (**smart**: by name or UUID)
- `ssh_keys_delete` - Remove SSH key (**smart**: by name or UUID)

### Backup Management (2 tools)
- `backups_list` - List all backups
- `backups_get` - Get backup details

### Firewall Management (10 tools)
- `firewall_list_groups` - List firewall groups
- `firewall_get_group` - Get group details (**smart**: by description or UUID)
- `firewall_create_group` - Create firewall group
- `firewall_update_group` - Update group description (**smart**: by description or UUID)
- `firewall_delete_group` - Delete firewall group (**smart**: by description or UUID)
- `firewall_list_rules` - List rules in a group (**smart**: by description or UUID)
- `firewall_get_rule` - Get specific rule (**smart**: group by description or UUID)
- `firewall_create_rule` - Add firewall rule (**smart**: group by description or UUID)
- `firewall_delete_rule` - Remove firewall rule (**smart**: group by description or UUID)
- `firewall_setup_web_server_rules` - Quick setup for web servers (**smart**: group by description or UUID)

### Snapshot Management (6 tools)
- `snapshots_list` - List all snapshots
- `snapshots_get` - Get snapshot details (**smart**: by description or UUID)
- `snapshots_create` - Create instance snapshot
- `snapshots_create_from_url` - Create snapshot from URL
- `snapshots_update` - Update snapshot description (**smart**: by description or UUID)
- `snapshots_delete` - Delete snapshot (**smart**: by description or UUID)

### Region Information (4 tools)
- `regions_list` - List all available regions
- `regions_get_availability` - Check plan availability in region
- `regions_find_regions_with_plan` - Find regions for specific plan
- `regions_list_by_continent` - Filter regions by continent

### Reserved IP Management (12 tools)
- `reserved_ips_list` - List all reserved IPs
- `reserved_ips_get` - Get reserved IP details (**smart**: by IP address or UUID)
- `reserved_ips_create` - Reserve new IP address
- `reserved_ips_update` - Update reserved IP label (**smart**: by IP address or UUID)
- `reserved_ips_delete` - Release reserved IP (**smart**: by IP address or UUID)
- `reserved_ips_attach` - Attach IP to instance (**smart**: by IP address or UUID)
- `reserved_ips_detach` - Detach IP from instance (**smart**: by IP address or UUID)
- `reserved_ips_convert_instance_ip` - Convert instance IP to reserved
- `reserved_ips_list_by_region` - List IPs in specific region
- `reserved_ips_list_unattached` - List unattached IPs
- `reserved_ips_list_attached` - List attached IPs with instance info

## CLI Commands

```bash
# Domain management
mcp-vultr domains list
mcp-vultr domains info example.com
mcp-vultr domains create newdomain.com 192.168.1.100

# Record management
mcp-vultr records list example.com
mcp-vultr records add example.com A www 192.168.1.100
mcp-vultr records delete example.com record-id

# Zone file operations
mcp-vultr zones export example.com > example.zone
mcp-vultr zones import example.com example.zone

# Instance management (with smart identifier resolution)
mcp-vultr instances list
mcp-vultr instances create --region ewr --plan vc2-1c-1gb --os 387 --label web-server
mcp-vultr instances get web-server            # By label
mcp-vultr instances stop production.local     # By hostname
mcp-vultr instances reboot web-server        # By label

# SSH key management (with smart identifier resolution)
mcp-vultr ssh-keys list
mcp-vultr ssh-keys add laptop-key "ssh-rsa AAAAB3..."
mcp-vultr ssh-keys delete laptop-key         # By name

# Firewall management (with smart identifier resolution)
mcp-vultr firewall groups list
mcp-vultr firewall groups create "web-servers"
mcp-vultr firewall rules list web-servers    # By description
mcp-vultr firewall rules add web-servers --port 443 --protocol tcp

# Snapshot management (with smart identifier resolution)
mcp-vultr snapshots list
mcp-vultr snapshots create instance-id --description "backup-2024-01"
mcp-vultr snapshots delete backup-2024-01    # By description

# Reserved IP management (with smart identifier resolution)
mcp-vultr reserved-ips list
mcp-vultr reserved-ips create --region ewr --type v4 --label production-ip
mcp-vultr reserved-ips attach 192.168.1.100 instance-id  # By IP
mcp-vultr reserved-ips delete 192.168.1.100             # By IP

# Setup utilities
mcp-vultr setup-website example.com 192.168.1.100
mcp-vultr setup-email example.com mail.example.com

# Start MCP server
vultr-mcp-server
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
uv run pytest --cov=mcp_vultr --cov-report=html

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
from mcp_vultr import (
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

## Changelog

### v1.9.0 (Latest)
- **Feature**: Universal UUID lookup pattern across all modules - use human-readable names everywhere!
  - Instances: lookup by label or hostname
  - SSH Keys: lookup by name
  - Firewall Groups: lookup by description
  - Snapshots: lookup by description
  - Reserved IPs: lookup by IP address
- **Feature**: All UUID lookups use exact matching for safety
- **Enhancement**: Improved error messages when resources not found

### v1.8.1
- **Feature**: Smart identifier resolution for Reserved IPs
- **Fix**: Reserved IP tools now accept IP addresses directly

### v1.8.0
- **Feature**: Complete Reserved IP management (12 new tools)
- **Feature**: Support for IPv4 and IPv6 reserved IPs
- **Feature**: Convert existing instance IPs to reserved

### v1.1.0
- **Feature**: Zone file import/export functionality
- **Feature**: Standard DNS zone file format support

### v1.0.1
- **Major**: Migrated to FastMCP 2.0 framework
- **Feature**: Custom exception hierarchy for better error handling
- **Feature**: Enhanced IPv6 validation with ipaddress module
- **Feature**: HTTP request timeouts (30s total, 10s connect)
- **Feature**: Full uv package manager integration
- **Fix**: Resolved event loop issues with FastMCP

### v1.0.0
- Initial release with complete MCP server implementation
- Support for DNS, Instances, SSH Keys, Backups, Firewall, Snapshots, Regions
- CLI interface and Python client library

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Links

- [GitHub Repository](https://github.com/rsp2k/mcp-vultr)
- [PyPI Package](https://pypi.org/project/mcp-vultr/)
- [Vultr API Documentation](https://www.vultr.com/api/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [uv Package Manager](https://docs.astral.sh/uv/)