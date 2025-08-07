# Vultr MCP

A comprehensive Model Context Protocol (MCP) server for managing Vultr services through natural language interfaces.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

## Features

- **Complete MCP Server**: Full Model Context Protocol implementation with 350+ tools across 26 service modules
- **Comprehensive Service Coverage**: 
  - **DNS Management**: Full DNS record management (A, AAAA, CNAME, MX, TXT, NS, SRV)
  - **Instance Management**: Create, manage, and control compute instances
  - **SSH Keys**: Manage SSH keys for secure access
  - **Backups**: Create and manage instance backups
  - **Firewall**: Configure firewall groups and rules
  - **Snapshots**: Create and manage instance snapshots
  - **Regions**: Query region availability and capabilities
  - **Reserved IPs**: Manage static IP addresses
  - **Container Registry**: Manage container registries and Docker credentials
  - **Block Storage**: Manage persistent storage volumes with attach/detach
  - **VPCs & VPC 2.0**: Manage virtual private cloud networks and instance connectivity
  - **ISO Images**: Upload, manage, and deploy custom ISO images
  - **Operating Systems**: Browse and select from available OS templates
  - **Plans**: Compare and select hosting plans with filtering
  - **Startup Scripts**: Create and manage server initialization scripts
  - **Billing & Account**: Monitor costs, analyze spending, and manage account details
  - **Bare Metal Servers**: Deploy and manage dedicated physical servers
  - **CDN & Edge Delivery**: Accelerate content delivery with global edge caching
  - **Kubernetes**: Container orchestration with cluster and node pool management
  - **Load Balancers**: High availability load balancing with SSL and health checks
  - **Managed Databases**: MySQL, PostgreSQL, Redis, and Kafka database services
  - **Object Storage**: S3-compatible object storage with bucket management
  - **Serverless Inference**: AI/ML inference services with usage analytics
  - **Storage Gateways**: NFS storage gateways with export management
  - **Marketplace**: Browse and deploy marketplace applications
  - **Account Management**: Subaccount and user management with permissions
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
- **Container Registries**: Use registry name instead of UUID
- **Block Storage**: Use volume label instead of UUID
- **VPCs & VPC 2.0**: Use network description instead of UUID
- **Startup Scripts**: Use script name instead of UUID
- **Bare Metal Servers**: Use server label or hostname instead of UUID
- **CDN Zones**: Use origin domain or CDN domain instead of UUID
- **Kubernetes Clusters**: Use cluster name or label instead of UUID
- **Load Balancers**: Use load balancer name or label instead of UUID
- **Databases**: Use database name or label instead of UUID
- **Object Storage**: Use storage name or label instead of UUID
- **Inference Services**: Use service name or label instead of UUID
- **Storage Gateways**: Use gateway name or label instead of UUID
- **Subaccounts**: Use subaccount name or email instead of UUID
- **Users**: Use email address instead of UUID

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

The MCP server provides 200+ tools across 18 service modules. All tools support **smart identifier resolution** - you can use human-readable names instead of UUIDs!

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

### Container Registry Management (11 tools)
- `container_registry_list` - List all container registries
- `container_registry_get` - Get registry details (**smart**: by name or UUID)
- `container_registry_create` - Create new container registry
- `container_registry_update` - Update registry plan (**smart**: by name or UUID)
- `container_registry_delete` - Delete registry (**smart**: by name or UUID)
- `container_registry_list_plans` - List available plans
- `container_registry_generate_docker_credentials` - Generate Docker login credentials (**smart**: by name or UUID)
- `container_registry_generate_kubernetes_credentials` - Generate Kubernetes secret YAML (**smart**: by name or UUID)
- `container_registry_get_docker_login_command` - Get ready-to-use Docker login command (**smart**: by name or UUID)
- `container_registry_get_registry_info` - Get comprehensive registry information (**smart**: by name or UUID)
- `container_registry_get_usage_examples` - Get Docker push/pull examples (**smart**: by name or UUID)

### Block Storage Management (12 tools)
- `block_storage_list` - List all block storage volumes
- `block_storage_get` - Get volume details (**smart**: by label or UUID)
- `block_storage_create` - Create new block storage volume
- `block_storage_update` - Update volume size or label (**smart**: by label or UUID)
- `block_storage_delete` - Delete volume (**smart**: by label or UUID)
- `block_storage_attach` - Attach volume to instance (**smart**: by label or UUID)
- `block_storage_detach` - Detach volume from instance (**smart**: by label or UUID)
- `block_storage_list_by_region` - List volumes in specific region
- `block_storage_list_unattached` - List unattached volumes
- `block_storage_list_attached` - List attached volumes with instance info
- `block_storage_get_volume_status` - Get comprehensive volume status (**smart**: by label or UUID)
- `block_storage_get_mounting_instructions` - Get Linux mounting instructions (**smart**: by label or UUID)

### VPC Management (15 tools)
- `vpcs_list_vpcs` - List all VPC networks
- `vpcs_get_vpc` - Get VPC details (**smart**: by description or UUID)
- `vpcs_create_vpc` - Create new VPC network
- `vpcs_update_vpc` - Update VPC description (**smart**: by description or UUID)
- `vpcs_delete_vpc` - Delete VPC network (**smart**: by description or UUID)
- `vpcs_list_vpc2s` - List all VPC 2.0 networks
- `vpcs_get_vpc2` - Get VPC 2.0 details (**smart**: by description or UUID)
- `vpcs_create_vpc2` - Create new VPC 2.0 network
- `vpcs_update_vpc2` - Update VPC 2.0 description (**smart**: by description or UUID)
- `vpcs_delete_vpc2` - Delete VPC 2.0 network (**smart**: by description or UUID)
- `vpcs_attach_instance` - Attach instance to VPC/VPC 2.0 (**smart**: by descriptions or UUIDs)
- `vpcs_detach_instance` - Detach instance from VPC/VPC 2.0 (**smart**: by descriptions or UUIDs)
- `vpcs_list_vpc_instances` - List instances attached to VPC (**smart**: by description or UUID)
- `vpcs_list_vpc2_instances` - List instances attached to VPC 2.0 (**smart**: by description or UUID)
- `vpcs_get_vpc_instance_info` - Get instance network info in VPC (**smart**: by descriptions or UUIDs)

### ISO Management (8 tools)
- `iso_list_isos` - List all available ISO images
- `iso_get_iso` - Get ISO details by ID
- `iso_create_iso` - Create new ISO from URL
- `iso_delete_iso` - Delete ISO image
- `iso_list_public_isos` - List Vultr-provided public ISOs
- `iso_list_custom_isos` - List user-uploaded custom ISOs
- `iso_get_iso_by_name` - Get ISO by name or filename
- `iso_search_isos` - Search ISOs by name

### Operating Systems (9 tools)
- `os_list_operating_systems` - List all available operating systems
- `os_get_operating_system` - Get OS details by ID
- `os_list_linux_os` - List Linux distributions
- `os_list_windows_os` - List Windows operating systems
- `os_search_os_by_name` - Search OS by name (partial match)
- `os_get_os_by_name` - Get OS by exact name match
- `os_list_application_images` - List one-click application images
- `os_list_os_by_family` - List OS by family (ubuntu, centos, etc.)
- `os_get_os_recommendations` - Get recommended OS for use case

### Plans (12 tools)
- `plans_list_plans` - List all available hosting plans
- `plans_get_plan` - Get plan details by ID
- `plans_list_vc2_plans` - List VC2 (Virtual Cloud Compute) plans
- `plans_list_vhf_plans` - List VHF (High Frequency) plans
- `plans_list_voc_plans` - List VOC (Optimized Cloud) plans
- `plans_search_plans_by_specs` - Search plans by CPU/RAM/disk specs
- `plans_get_plan_by_type_and_spec` - Get plans by type and specific specs
- `plans_get_cheapest_plan` - Find the most cost-effective plan
- `plans_get_plans_by_region_availability` - Get plans available in region
- `plans_compare_plans` - Compare multiple plans side by side
- `plans_filter_by_performance` - Filter plans by performance criteria
- `plans_get_plan_recommendations` - Get recommended plans for workload

### Startup Scripts (12 tools)
- `startup_scripts_list_startup_scripts` - List all startup scripts
- `startup_scripts_get_startup_script` - Get script details (**smart**: by name or UUID)
- `startup_scripts_create_startup_script` - Create new startup script
- `startup_scripts_update_startup_script` - Update script (**smart**: by name or UUID)
- `startup_scripts_delete_startup_script` - Delete script (**smart**: by name or UUID)
- `startup_scripts_list_boot_scripts` - List boot startup scripts
- `startup_scripts_list_pxe_scripts` - List PXE startup scripts
- `startup_scripts_search_startup_scripts` - Search scripts by name/content
- `startup_scripts_create_common_startup_script` - Create from templates
- `startup_scripts_get_startup_script_content` - Get script content only (**smart**: by name or UUID)
- `startup_scripts_clone_startup_script` - Clone existing script (**smart**: by name or UUID)
- `startup_scripts_validate_script` - Validate script syntax and security

### Billing & Account Management (13 tools)
- `billing_get_account_info` - Get account information and details
- `billing_get_current_balance` - Get current balance and payment status
- `billing_list_billing_history` - List billing transactions and charges
- `billing_list_invoices` - List all invoices
- `billing_get_invoice` - Get specific invoice details
- `billing_list_invoice_items` - List items in specific invoice
- `billing_get_monthly_usage_summary` - Get monthly cost breakdown
- `billing_get_current_month_summary` - Get current month usage summary
- `billing_get_last_month_summary` - Get previous month usage summary
- `billing_analyze_spending_trends` - Analyze spending patterns and trends
- `billing_get_cost_breakdown_by_service` - Get service-wise cost analysis
- `billing_get_payment_summary` - Get payment history and account status
- `billing_generate_cost_optimization_tips` - Get personalized cost saving recommendations

### Bare Metal Server Management (20 tools)
- `bare_metal_list_bare_metal_servers` - List all bare metal servers
- `bare_metal_get_bare_metal_server` - Get server details (**smart**: by label, hostname, or UUID)
- `bare_metal_create_bare_metal_server` - Create new bare metal server
- `bare_metal_update_bare_metal_server` - Update server configuration (**smart**: by label, hostname, or UUID)
- `bare_metal_delete_bare_metal_server` - Delete server (**smart**: by label, hostname, or UUID)
- `bare_metal_start_bare_metal_server` - Start server (**smart**: by label, hostname, or UUID)
- `bare_metal_stop_bare_metal_server` - Stop server (**smart**: by label, hostname, or UUID)
- `bare_metal_reboot_bare_metal_server` - Reboot server (**smart**: by label, hostname, or UUID)
- `bare_metal_reinstall_bare_metal_server` - Reinstall server OS (**smart**: by label, hostname, or UUID)
- `bare_metal_get_bare_metal_bandwidth` - Get bandwidth usage (**smart**: by label, hostname, or UUID)
- `bare_metal_get_bare_metal_neighbors` - Get physical neighbors (**smart**: by label, hostname, or UUID)
- `bare_metal_get_bare_metal_user_data` - Get user data (**smart**: by label, hostname, or UUID)
- `bare_metal_list_bare_metal_plans` - List available bare metal plans
- `bare_metal_get_bare_metal_plan` - Get specific plan details
- `bare_metal_search_bare_metal_plans` - Search plans by specs and cost
- `bare_metal_list_bare_metal_servers_by_status` - List servers by status
- `bare_metal_list_bare_metal_servers_by_region` - List servers in region
- `bare_metal_get_bare_metal_server_summary` - Get comprehensive server summary (**smart**: by label, hostname, or UUID)
- `bare_metal_get_server_performance_metrics` - Get performance and usage metrics (**smart**: by label, hostname, or UUID)
- `bare_metal_manage_server_lifecycle` - Complete server lifecycle management (**smart**: by label, hostname, or UUID)

### CDN & Edge Delivery Management (16 tools)
- `cdn_list_cdn_zones` - List all CDN zones
- `cdn_get_cdn_zone` - Get CDN zone details (**smart**: by origin domain, CDN domain, or UUID)
- `cdn_create_cdn_zone` - Create new CDN zone with configuration
- `cdn_update_cdn_zone` - Update CDN zone settings (**smart**: by origin domain, CDN domain, or UUID)
- `cdn_delete_cdn_zone` - Delete CDN zone (**smart**: by origin domain, CDN domain, or UUID)
- `cdn_purge_cdn_zone` - Purge all cached content (**smart**: by origin domain, CDN domain, or UUID)
- `cdn_get_cdn_zone_stats` - Get performance statistics (**smart**: by origin domain, CDN domain, or UUID)
- `cdn_get_cdn_zone_logs` - Get access logs with filtering (**smart**: by origin domain, CDN domain, or UUID)
- `cdn_create_cdn_ssl_certificate` - Upload SSL certificate (**smart**: by origin domain, CDN domain, or UUID)
- `cdn_get_cdn_ssl_certificate` - Get SSL certificate info (**smart**: by origin domain, CDN domain, or UUID)
- `cdn_delete_cdn_ssl_certificate` - Remove SSL certificate (**smart**: by origin domain, CDN domain, or UUID)
- `cdn_get_cdn_available_regions` - List available CDN regions
- `cdn_analyze_cdn_performance` - Analyze performance with recommendations (**smart**: by origin domain, CDN domain, or UUID)
- `cdn_setup_cdn_for_website` - Quick CDN setup for websites
- `cdn_get_cdn_zone_summary` - Get comprehensive zone summary (**smart**: by origin domain, CDN domain, or UUID)

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

# Container registry management (with smart identifier resolution)
mcp-vultr container-registry list
mcp-vultr container-registry create my-registry start_up ewr
mcp-vultr container-registry docker-login my-registry    # By name
mcp-vultr container-registry docker-login my-registry --expiry 3600 --read-only

# Block storage management (with smart identifier resolution)
mcp-vultr block-storage list
mcp-vultr block-storage create ewr 50 --label database-storage
mcp-vultr block-storage attach database-storage web-server  # By label
mcp-vultr block-storage mount-help database-storage        # Get mounting instructions

# VPC management (with smart identifier resolution)
mcp-vultr vpcs list
mcp-vultr vpcs create ewr production-network --vpc-type vpc2
mcp-vultr vpcs info production-network              # By description
mcp-vultr vpcs attach web-server production-network  # Attach instance by label to VPC by description
mcp-vultr vpcs list-instances production-network    # List instances in VPC

# ISO management
mcp-vultr iso list --filter public
mcp-vultr iso list --filter custom
mcp-vultr iso create https://example.com/custom.iso

# Operating system management
mcp-vultr os list --filter linux
mcp-vultr os list --filter windows
mcp-vultr os list --filter apps

# Plans management
mcp-vultr plans list --type vc2 --min-vcpus 2 --max-cost 20
mcp-vultr plans list --type vhf
mcp-vultr plans list --min-ram 4096

# Startup scripts management
mcp-vultr startup-scripts list --type boot
mcp-vultr startup-scripts create "Docker Setup" "#!/bin/bash\napt update && apt install -y docker.io"
mcp-vultr startup-scripts delete "Docker Setup"   # By name

# Billing and account management
mcp-vultr billing account                         # Show account info and balance
mcp-vultr billing history --days 7               # Show recent transactions
mcp-vultr billing invoices --limit 5             # List recent invoices  
mcp-vultr billing monthly --year 2024 --month 12 # Monthly usage summary
mcp-vultr billing trends --months 6              # Analyze spending trends

# Bare metal server management (with smart identifier resolution)
mcp-vultr bare-metal list --status active        # List active servers
mcp-vultr bare-metal get database-server         # Get server by label
mcp-vultr bare-metal create ewr vbm-4c-32gb --label "database-server" --os-id 387
mcp-vultr bare-metal start database-server       # Start by label
mcp-vultr bare-metal reboot prod.example.com     # Reboot by hostname
mcp-vultr bare-metal plans --min-ram 32 --max-cost 200  # Filter plans

# CDN management (with smart identifier resolution)
mcp-vultr cdn list                              # List all CDN zones
mcp-vultr cdn get example.com                   # Get zone by origin domain
mcp-vultr cdn create example.com --regions us,eu --gzip --security
mcp-vultr cdn purge example.com                 # Purge cache by domain
mcp-vultr cdn stats example.com                 # Get performance stats
mcp-vultr cdn logs example.com --days 7         # Get access logs
mcp-vultr cdn ssl upload example.com cert.pem key.pem  # Upload SSL
mcp-vultr cdn regions                           # List available regions

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

### v2.0.0 (Latest)
- **MAJOR RELEASE**: Complete Vultr API coverage with 8 new service modules (350+ tools across 26 modules)
- **Feature**: Kubernetes cluster management (25 new tools) - Full cluster lifecycle, node pools, auto-scaling, cost analysis
- **Feature**: Load Balancer management (16 new tools) - HTTP/HTTPS/TCP load balancing, SSL, health checks
- **Feature**: Managed Databases (41 new tools) - MySQL, PostgreSQL, Redis, Kafka with user management and backups
- **Feature**: Object Storage (12 new tools) - S3-compatible storage with bucket management and access keys
- **Feature**: Serverless Inference (12 new tools) - AI/ML inference services with usage monitoring and optimization
- **Feature**: Storage Gateways (14 new tools) - NFS storage gateways with export management and security
- **Feature**: Marketplace Applications (11 new tools) - Browse, search, and deploy marketplace applications
- **Feature**: Account Management (23 new tools) - Subaccount and user management with permissions and security
- **Enhancement**: Complete Vultr API v2 coverage achieved with smart identifier resolution across all services
- **Enhancement**: All modules integrated with FastMCP framework following consistent patterns

### v1.16.0
- **Feature**: Complete CDN & Edge Delivery management (16 new tools)
  - Global content delivery network with edge caching
  - Smart identifier resolution by origin domain or CDN domain
  - SSL certificate management for secure delivery
  - Performance analytics with cache hit ratio analysis
  - Content purging and access log analysis
  - Security features: bot blocking, IP filtering, CORS policies
  - Gzip compression for faster content delivery
  - Multi-region CDN deployment capabilities
  - CLI commands for comprehensive CDN management
- **Feature**: CDN performance optimization recommendations
- **Feature**: Website-optimized CDN setup with best practices
- **Feature**: CDN module integrated with FastMCP framework

### v1.15.0
- **Feature**: Complete Bare Metal Server management (20 new tools)
  - Deploy and manage dedicated physical servers
  - Smart identifier resolution by server label or hostname
  - Full lifecycle management: create, start, stop, reboot, reinstall
  - Performance monitoring with bandwidth and neighbor analysis
  - Bare metal plan comparison and selection
  - CLI commands for comprehensive server management
- **Feature**: Physical server insights and analytics
- **Feature**: Hardware resource monitoring and optimization
- **Feature**: Bare metal module integrated with FastMCP framework

### v1.14.0
- **Feature**: Complete Billing & Account management (13 new tools)
  - Monitor account balance, pending charges, and payment history
  - Analyze monthly usage summaries with service breakdowns
  - Track spending trends and patterns over time
  - Cost optimization recommendations and insights
  - Invoice management and detailed billing history
  - CLI commands for financial monitoring and analysis
- **Feature**: Advanced cost analytics with trend analysis
- **Feature**: Service-wise cost breakdown and recommendations
- **Feature**: Billing module integrated with FastMCP framework

### v1.13.0
- **Feature**: Complete ISO image management (8 new tools)
  - Upload custom ISOs from URLs and manage existing ones
  - List and filter public vs custom ISO images
  - Smart search and identification capabilities
  - CLI commands for ISO operations
- **Feature**: Operating Systems browsing (9 new tools)
  - Browse all available OS templates and distributions
  - Filter by type (Linux, Windows, Applications)
  - Search by name and family groupings
  - Recommendations for optimal OS selection
- **Feature**: Hosting Plans comparison (12 new tools)
  - Compare VC2, VHF, and VOC plan types
  - Search and filter by specs (CPU, RAM, disk, cost)
  - Region availability checking
  - Side-by-side plan comparisons and recommendations
- **Feature**: Startup Scripts automation (12 new tools)
  - Create and manage server initialization scripts
  - Smart identifier resolution by script name
  - Template-based script creation (Docker, Node.js, security)
  - Boot and PXE script type support
- **Feature**: All new modules integrated with FastMCP framework
- **Feature**: Comprehensive CLI commands for all new functionality

### v1.12.0
- **Feature**: Complete VPC and VPC 2.0 management (15 new tools)
  - Full CRUD operations for both VPC and VPC 2.0 networks
  - Instance attachment/detachment to VPC networks
  - Smart identifier resolution by network description
  - Cross-service integration with instances
  - CLI commands for VPC management with dual VPC type support
- **Feature**: VPC integration with FastMCP framework
- **Feature**: Enhanced networking capabilities with IPv4 support

### v1.11.0
- **Feature**: Complete Block Storage management (12 new tools)
  - Full CRUD operations for block storage volumes
  - Attach/detach volumes to/from instances with live option
  - Smart identifier resolution by volume label
  - Linux mounting instructions with automated scripts
  - CLI commands for volume management
- **Feature**: Block storage integration with FastMCP
- **Feature**: Volume status monitoring and cost tracking

### v1.10.0
- **Feature**: Complete Container Registry management (11 new tools)
  - Full CRUD operations for container registries
  - Docker and Kubernetes credentials generation
  - Smart identifier resolution by registry name
  - CLI commands for registry management
- **Feature**: Container registry integration with FastMCP
- **Feature**: Docker login command generation with expiry control

### v1.9.0
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