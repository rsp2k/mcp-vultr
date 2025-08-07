"""
Command Line Interface for Vultr DNS MCP.

This module provides CLI commands for running the MCP server and
performing DNS operations directly from the command line.
"""

import asyncio
import os
import sys
from typing import Optional

import click

from ._version import __version__
from .client import VultrDNSClient
from .server import run_server


@click.group()
@click.version_option(__version__)
@click.option(
    "--api-key",
    envvar="VULTR_API_KEY",
    help="Vultr API key (or set VULTR_API_KEY environment variable)"
)
@click.pass_context
def cli(ctx: click.Context, api_key: Optional[str]):
    """Vultr DNS MCP - Manage Vultr DNS through Model Context Protocol."""
    ctx.ensure_object(dict)
    ctx.obj['api_key'] = api_key


@cli.command()
@click.pass_context
def server(ctx: click.Context):
    """Start the Vultr DNS MCP server."""
    api_key = ctx.obj.get('api_key')
    
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        click.echo("Set it as an environment variable or use --api-key option", err=True)
        sys.exit(1)
    
    click.echo(f"🚀 Starting Vultr DNS MCP Server...")
    click.echo(f"🔑 API Key: {api_key[:8]}...")
    click.echo(f"🔄 Press Ctrl+C to stop")
    
    try:
        run_server(api_key)
    except KeyboardInterrupt:
        click.echo("\n👋 Server stopped")
    except Exception as e:
        click.echo(f"❌ Server error: {e}", err=True)
        sys.exit(1)


@cli.group()
@click.pass_context
def domains(ctx: click.Context):
    """Manage DNS domains."""
    pass


@domains.command("list")
@click.pass_context
def list_domains(ctx: click.Context):
    """List all domains in your account."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _list_domains():
        client = VultrDNSClient(api_key)
        try:
            domains_list = await client.domains()
            
            if not domains_list:
                click.echo("No domains found")
                return
            
            click.echo(f"Found {len(domains_list)} domain(s):")
            for domain in domains_list:
                domain_name = domain.get('domain', 'Unknown')
                created = domain.get('date_created', 'Unknown')
                click.echo(f"  • {domain_name} (created: {created})")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_list_domains())


@domains.command("info")
@click.argument("domain")
@click.pass_context
def domain_info(ctx: click.Context, domain: str):
    """Get detailed information about a domain."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _domain_info():
        client = VultrDNSClient(api_key)
        try:
            summary = await client.get_domain_summary(domain)
            
            if "error" in summary:
                click.echo(f"Error: {summary['error']}", err=True)
                sys.exit(1)
            
            click.echo(f"Domain: {domain}")
            click.echo(f"Total Records: {summary['total_records']}")
            
            if summary['record_types']:
                click.echo("Record Types:")
                for record_type, count in summary['record_types'].items():
                    click.echo(f"  • {record_type}: {count}")
            
            config = summary['configuration']
            click.echo("Configuration:")
            click.echo(f"  • Root domain record: {'✅' if config['has_root_record'] else '❌'}")
            click.echo(f"  • WWW subdomain: {'✅' if config['has_www_subdomain'] else '❌'}")
            click.echo(f"  • Email setup: {'✅' if config['has_email_setup'] else '❌'}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_domain_info())


@domains.command("create")
@click.argument("domain")
@click.argument("ip")
@click.pass_context
def create_domain(ctx: click.Context, domain: str, ip: str):
    """Create a new domain with default A record."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _create_domain():
        client = VultrDNSClient(api_key)
        try:
            result = await client.add_domain(domain, ip)
            
            if "error" in result:
                click.echo(f"Error creating domain: {result['error']}", err=True)
                sys.exit(1)
            
            click.echo(f"✅ Created domain {domain} with IP {ip}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_create_domain())


@cli.group()
@click.pass_context
def records(ctx: click.Context):
    """Manage DNS records."""
    pass


@records.command("list")
@click.argument("domain")
@click.option("--type", "record_type", help="Filter by record type")
@click.pass_context
def list_records(ctx: click.Context, domain: str, record_type: Optional[str]):
    """List DNS records for a domain."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _list_records():
        client = VultrDNSClient(api_key)
        try:
            if record_type:
                records_list = await client.find_records_by_type(domain, record_type)
            else:
                records_list = await client.records(domain)
            
            if not records_list:
                click.echo(f"No records found for {domain}")
                return
            
            click.echo(f"DNS records for {domain}:")
            for record in records_list:
                record_id = record.get('id', 'Unknown')
                r_type = record.get('type', 'Unknown')
                name = record.get('name', 'Unknown')
                data = record.get('data', 'Unknown')
                ttl = record.get('ttl', 'Unknown')
                
                click.echo(f"  • [{record_id}] {r_type:6} {name:20} ➜ {data} (TTL: {ttl})")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_list_records())


@records.command("add")
@click.argument("domain")
@click.argument("record_type")
@click.argument("name")
@click.argument("value")
@click.option("--ttl", type=int, help="Time to live in seconds")
@click.option("--priority", type=int, help="Priority for MX/SRV records")
@click.pass_context
def add_record(
    ctx: click.Context, 
    domain: str, 
    record_type: str, 
    name: str, 
    value: str,
    ttl: Optional[int],
    priority: Optional[int]
):
    """Add a new DNS record."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _add_record():
        client = VultrDNSClient(api_key)
        try:
            result = await client.add_record(domain, record_type, name, value, ttl, priority)
            
            if "error" in result:
                click.echo(f"Error creating record: {result['error']}", err=True)
                sys.exit(1)
            
            record_id = result.get('id', 'Unknown')
            click.echo(f"✅ Created {record_type} record [{record_id}]: {name} ➜ {value}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_add_record())


@records.command("delete")
@click.argument("domain")
@click.argument("record_id")
@click.confirmation_option(prompt="Are you sure you want to delete this record?")
@click.pass_context
def delete_record(ctx: click.Context, domain: str, record_id: str):
    """Delete a DNS record."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _delete_record():
        client = VultrDNSClient(api_key)
        try:
            success = await client.remove_record(domain, record_id)
            
            if success:
                click.echo(f"✅ Deleted record {record_id}")
            else:
                click.echo(f"❌ Failed to delete record {record_id}", err=True)
                sys.exit(1)
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_delete_record())


@cli.group()
def container_registry():
    """Manage Vultr container registries."""
    pass


@container_registry.command("list")
@click.pass_context
def cr_list(ctx: click.Context):
    """List all container registries."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _list_registries():
        from .server import VultrDNSServer
        client = VultrDNSServer(api_key)
        try:
            registries = await client.list_container_registries()
            
            if not registries:
                click.echo("No container registries found.")
                return
            
            click.echo(f"\n📦 Container Registries ({len(registries)}):")
            click.echo("-" * 60)
            
            for registry in registries:
                click.echo(f"Name: {registry.get('name', 'N/A')}")
                click.echo(f"ID: {registry.get('id', 'N/A')}")
                click.echo(f"URN: {registry.get('urn', 'N/A')}")
                click.echo(f"Storage Used: {registry.get('storage', {}).get('used_mb', 0)} MB")
                click.echo(f"Storage Limit: {registry.get('storage', {}).get('limit_mb', 0)} MB")
                click.echo(f"Public: {registry.get('public', False)}")
                click.echo(f"Created: {registry.get('date_created', 'N/A')}")
                click.echo("-" * 60)
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_list_registries())


@container_registry.command("create")
@click.argument("name")
@click.argument("plan")
@click.argument("region")
@click.pass_context
def cr_create(ctx: click.Context, name: str, plan: str, region: str):
    """Create a new container registry."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _create_registry():
        from .server import VultrDNSServer
        client = VultrDNSServer(api_key)
        
        try:
            click.echo(f"Creating container registry '{name}' in {region} with {plan} plan...")
            registry = await client.create_container_registry(name, plan, region)
            
            click.echo(f"✅ Container registry created successfully!")
            click.echo(f"Name: {registry.get('name', 'N/A')}")
            click.echo(f"ID: {registry.get('id', 'N/A')}")
            click.echo(f"URN: {registry.get('urn', 'N/A')}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_create_registry())


@container_registry.command("docker-login")
@click.argument("registry_identifier")
@click.option("--expiry", type=int, help="Expiration time in seconds")
@click.option("--read-only", is_flag=True, help="Generate read-only credentials")
@click.pass_context
def cr_docker_login(ctx: click.Context, registry_identifier: str, expiry: Optional[int], read_only: bool):
    """Generate Docker login command for registry access."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _docker_login():
        from .server import VultrDNSServer
        from .container_registry import create_container_registry_mcp
        
        client = VultrDNSServer(api_key)
        mcp = create_container_registry_mcp(client)
        
        try:
            result = await mcp._tool_handlers["get_docker_login_command"]["func"](
                registry_identifier, expiry, not read_only
            )
            
            click.echo(f"\n🐳 Docker Login Command:")
            click.echo("-" * 60)
            click.echo(result["login_command"])
            click.echo("-" * 60)
            click.echo(f"Registry URL: {result['registry_url']}")
            click.echo(f"Username: {result['username']}")
            click.echo(f"Access: {result['access_type']}")
            if result.get('expires_in_seconds'):
                click.echo(f"Expires in: {result['expires_in_seconds']} seconds")
            else:
                click.echo("Expires: Never")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_docker_login())


@cli.group()
def block_storage():
    """Manage Vultr block storage volumes."""
    pass


@block_storage.command("list")
@click.pass_context
def bs_list(ctx: click.Context):
    """List all block storage volumes."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _list_volumes():
        from .server import VultrDNSServer
        client = VultrDNSServer(api_key)
        try:
            volumes = await client.list_block_storage()
            
            if not volumes:
                click.echo("No block storage volumes found.")
                return
            
            click.echo(f"\n💾 Block Storage Volumes ({len(volumes)}):")
            click.echo("-" * 70)
            
            for volume in volumes:
                status_emoji = "🟢" if volume.get("status") == "active" else "🟡"
                attached_emoji = "🔗" if volume.get("attached_to_instance") else "⭕"
                
                click.echo(f"{status_emoji} {volume.get('label', 'unlabeled')}")
                click.echo(f"   ID: {volume.get('id', 'N/A')}")
                click.echo(f"   Size: {volume.get('size_gb', 0)} GB")
                click.echo(f"   Region: {volume.get('region', 'N/A')}")
                click.echo(f"   Status: {volume.get('status', 'N/A')}")
                click.echo(f"   {attached_emoji} {'Attached to: ' + volume.get('attached_to_instance', '') if volume.get('attached_to_instance') else 'Not attached'}")
                click.echo(f"   Cost: ${volume.get('cost_per_month', 0)}/month")
                click.echo(f"   Created: {volume.get('date_created', 'N/A')}")
                click.echo("-" * 70)
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_list_volumes())


@block_storage.command("get")
@click.argument("volume_identifier")
@click.pass_context
def bs_get(ctx: click.Context, volume_identifier: str):
    """Get block storage volume details (by label or ID)."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _get_volume():
        from .server import VultrDNSServer
        from .block_storage import create_block_storage_mcp
        
        client = VultrDNSServer(api_key)
        mcp = create_block_storage_mcp(client)
        
        try:
            volume = await mcp._tool_handlers["get"]["func"](volume_identifier)
            
            status_emoji = "🟢" if volume.get("status") == "active" else "🟡"
            attached_emoji = "🔗" if volume.get("attached_to_instance") else "⭕"
            
            click.echo(f"\n💾 Block Storage Volume: {volume.get('label', 'unlabeled')}")
            click.echo("-" * 70)
            click.echo(f"{status_emoji} Status: {volume.get('status', 'N/A')}")
            click.echo(f"   ID: {volume.get('id', 'N/A')}")
            click.echo(f"   Size: {volume.get('size_gb', 0)} GB")
            click.echo(f"   Region: {volume.get('region', 'N/A')}")
            click.echo(f"   {attached_emoji} {'Attached to: ' + volume.get('attached_to_instance', '') if volume.get('attached_to_instance') else 'Not attached'}")
            click.echo(f"   Cost: ${volume.get('cost_per_month', 0)}/month")
            click.echo(f"   Created: {volume.get('date_created', 'N/A')}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_get_volume())


@block_storage.command("create")
@click.argument("region")
@click.argument("size_gb", type=int)
@click.option("--label", help="Label for the volume")
@click.option("--block-type", help="Block storage type")
@click.pass_context
def bs_create(ctx: click.Context, region: str, size_gb: int, label: Optional[str], block_type: Optional[str]):
    """Create a new block storage volume."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _create_volume():
        from .server import VultrDNSServer
        client = VultrDNSServer(api_key)
        
        try:
            click.echo(f"Creating {size_gb}GB block storage volume in {region}...")
            if label:
                click.echo(f"Label: {label}")
            if block_type:
                click.echo(f"Type: {block_type}")
            
            volume = await client.create_block_storage(region, size_gb, label, block_type)
            
            click.echo(f"✅ Block storage volume created successfully!")
            click.echo(f"ID: {volume.get('id', 'N/A')}")
            click.echo(f"Label: {volume.get('label', 'unlabeled')}")
            click.echo(f"Size: {volume.get('size_gb', 0)} GB")
            click.echo(f"Cost: ${volume.get('cost_per_month', 0)}/month")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_create_volume())


@block_storage.command("attach")
@click.argument("volume_identifier")
@click.argument("instance_identifier")
@click.option("--no-live", is_flag=True, help="Require reboot to attach")
@click.pass_context
def bs_attach(ctx: click.Context, volume_identifier: str, instance_identifier: str, no_live: bool):
    """Attach block storage volume to an instance."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _attach_volume():
        from .server import VultrDNSServer
        from .block_storage import create_block_storage_mcp
        
        client = VultrDNSServer(api_key)
        mcp = create_block_storage_mcp(client)
        
        try:
            result = await mcp._tool_handlers["attach"]["func"](
                volume_identifier, instance_identifier, not no_live
            )
            click.echo(f"✅ {result['message']}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_attach_volume())


@block_storage.command("detach")
@click.argument("volume_identifier")
@click.option("--no-live", is_flag=True, help="Require reboot to detach")
@click.pass_context
def bs_detach(ctx: click.Context, volume_identifier: str, no_live: bool):
    """Detach block storage volume from its instance."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _detach_volume():
        from .server import VultrDNSServer
        from .block_storage import create_block_storage_mcp
        
        client = VultrDNSServer(api_key)
        mcp = create_block_storage_mcp(client)
        
        try:
            result = await mcp._tool_handlers["detach"]["func"](
                volume_identifier, not no_live
            )
            click.echo(f"✅ {result['message']}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_detach_volume())


@block_storage.command("mount-help")
@click.argument("volume_identifier")
@click.pass_context
def bs_mount_help(ctx: click.Context, volume_identifier: str):
    """Get mounting instructions for a block storage volume."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _mount_help():
        from .server import VultrDNSServer
        from .block_storage import create_block_storage_mcp
        
        client = VultrDNSServer(api_key)
        mcp = create_block_storage_mcp(client)
        
        try:
            instructions = await mcp._tool_handlers["get_mounting_instructions"]["func"](volume_identifier)
            
            volume_info = instructions["volume_info"]
            click.echo(f"\n💾 Mounting Instructions for '{volume_info['label']}'")
            click.echo("=" * 70)
            
            if instructions.get("warning"):
                click.echo(f"⚠️  {instructions['warning']}")
                click.echo()
            
            click.echo("📋 Prerequisites:")
            for prereq in instructions["prerequisites"]:
                click.echo(f"   • {prereq}")
            
            click.echo(f"\n🔧 Commands:")
            for desc, cmd in instructions["commands"].items():
                click.echo(f"   {desc.replace('_', ' ').title()}: {cmd}")
            
            click.echo(f"\n📝 Complete Script:")
            click.echo("-" * 70)
            click.echo(instructions["full_script"])
            click.echo("-" * 70)
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_mount_help())


@cli.group()
def vpcs():
    """Manage Vultr VPCs and VPC 2.0 networks."""
    pass


@vpcs.command("list")
@click.option("--vpc-type", type=click.Choice(["vpc", "vpc2", "all"]), default="all", help="Type of VPCs to list")
@click.pass_context
def vpcs_list(ctx: click.Context, vpc_type: str):
    """List VPCs and/or VPC 2.0 networks."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _list_networks():
        from .server import VultrDNSServer
        client = VultrDNSServer(api_key)
        try:
            vpcs = []
            vpc2s = []
            
            if vpc_type in ["vpc", "all"]:
                vpcs = await client.list_vpcs()
            if vpc_type in ["vpc2", "all"]:
                vpc2s = await client.list_vpc2s()
            
            if not vpcs and not vpc2s:
                click.echo("No VPC networks found.")
                return
            
            if vpcs:
                click.echo(f"\n🌐 VPCs ({len(vpcs)}):")
                click.echo("-" * 70)
                for vpc in vpcs:
                    click.echo(f"📡 {vpc.get('description', 'unlabeled')}")
                    click.echo(f"   ID: {vpc.get('id', 'N/A')}")
                    click.echo(f"   Region: {vpc.get('region', 'N/A')}")
                    click.echo(f"   Subnet: {vpc.get('v4_subnet', 'N/A')}/{vpc.get('v4_subnet_mask', 'N/A')}")
                    click.echo(f"   Created: {vpc.get('date_created', 'N/A')}")
                    click.echo("-" * 70)
            
            if vpc2s:
                click.echo(f"\n🌐 VPC 2.0 Networks ({len(vpc2s)}):")
                click.echo("-" * 70)
                for vpc2 in vpc2s:
                    click.echo(f"🚀 {vpc2.get('description', 'unlabeled')}")
                    click.echo(f"   ID: {vpc2.get('id', 'N/A')}")
                    click.echo(f"   Region: {vpc2.get('region', 'N/A')}")
                    click.echo(f"   IP Block: {vpc2.get('ip_block', 'N/A')}/{vpc2.get('prefix_length', 'N/A')}")
                    click.echo(f"   Created: {vpc2.get('date_created', 'N/A')}")
                    click.echo("-" * 70)
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_list_networks())


@vpcs.command("create")
@click.argument("region")
@click.argument("description")
@click.option("--vpc-type", type=click.Choice(["vpc", "vpc2"]), default="vpc", help="Type of VPC to create")
@click.option("--subnet", help="IPv4 subnet for VPC (e.g., 10.0.0.0)")
@click.option("--subnet-mask", type=int, help="Subnet mask for VPC (e.g., 24)")
@click.option("--ip-block", help="IP block for VPC 2.0 (e.g., 10.0.0.0)")
@click.option("--prefix-length", type=int, help="Prefix length for VPC 2.0 (e.g., 24)")
@click.pass_context
def vpcs_create(ctx: click.Context, region: str, description: str, vpc_type: str, 
                subnet: Optional[str], subnet_mask: Optional[int], 
                ip_block: Optional[str], prefix_length: Optional[int]):
    """Create a new VPC or VPC 2.0 network."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _create_network():
        from .server import VultrDNSServer
        client = VultrDNSServer(api_key)
        
        try:
            if vpc_type == "vpc2":
                click.echo(f"Creating VPC 2.0 '{description}' in {region}...")
                if ip_block:
                    click.echo(f"IP Block: {ip_block}/{prefix_length or 24}")
                network = await client.create_vpc2(region, description, "v4", ip_block, prefix_length)
                click.echo(f"✅ VPC 2.0 created successfully!")
                click.echo(f"ID: {network.get('id', 'N/A')}")
                click.echo(f"IP Block: {network.get('ip_block', 'N/A')}/{network.get('prefix_length', 'N/A')}")
            else:
                click.echo(f"Creating VPC '{description}' in {region}...")
                if subnet:
                    click.echo(f"Subnet: {subnet}/{subnet_mask or 24}")
                network = await client.create_vpc(region, description, subnet, subnet_mask)
                click.echo(f"✅ VPC created successfully!")
                click.echo(f"ID: {network.get('id', 'N/A')}")
                click.echo(f"Subnet: {network.get('v4_subnet', 'N/A')}/{network.get('v4_subnet_mask', 'N/A')}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_create_network())


@vpcs.command("attach")
@click.argument("vpc_identifier")
@click.argument("instance_identifier")
@click.option("--vpc-type", type=click.Choice(["vpc", "vpc2"]), default="vpc", help="Type of VPC")
@click.pass_context
def vpcs_attach(ctx: click.Context, vpc_identifier: str, instance_identifier: str, vpc_type: str):
    """Attach VPC/VPC 2.0 to an instance."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _attach_network():
        from .server import VultrDNSServer
        from .vpcs import create_vpcs_mcp
        
        client = VultrDNSServer(api_key)
        mcp = create_vpcs_mcp(client)
        
        try:
            result = await mcp._tool_handlers["attach_to_instance"]["func"](
                vpc_identifier, instance_identifier, vpc_type
            )
            click.echo(f"✅ {result['message']}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_attach_network())


@vpcs.command("detach")
@click.argument("vpc_identifier")
@click.argument("instance_identifier")
@click.option("--vpc-type", type=click.Choice(["vpc", "vpc2"]), default="vpc", help="Type of VPC")
@click.pass_context
def vpcs_detach(ctx: click.Context, vpc_identifier: str, instance_identifier: str, vpc_type: str):
    """Detach VPC/VPC 2.0 from an instance."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _detach_network():
        from .server import VultrDNSServer
        from .vpcs import create_vpcs_mcp
        
        client = VultrDNSServer(api_key)
        mcp = create_vpcs_mcp(client)
        
        try:
            result = await mcp._tool_handlers["detach_from_instance"]["func"](
                vpc_identifier, instance_identifier, vpc_type
            )
            click.echo(f"✅ {result['message']}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_detach_network())


@vpcs.command("list-instance")
@click.argument("instance_identifier")
@click.pass_context
def vpcs_list_instance(ctx: click.Context, instance_identifier: str):
    """List VPCs attached to an instance."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _list_instance_networks():
        from .server import VultrDNSServer
        from .vpcs import create_vpcs_mcp
        
        client = VultrDNSServer(api_key)
        mcp = create_vpcs_mcp(client)
        
        try:
            result = await mcp._tool_handlers["list_instance_networks"]["func"](instance_identifier)
            
            vpcs = result["vpcs"]
            vpc2s = result["vpc2s"]
            
            click.echo(f"\n🖥️  Instance Networks for: {instance_identifier}")
            click.echo("=" * 70)
            
            if vpcs:
                click.echo(f"\n📡 VPCs ({len(vpcs)}):")
                for vpc in vpcs:
                    click.echo(f"   • {vpc.get('description', 'unlabeled')} ({vpc.get('id', 'N/A')})")
            
            if vpc2s:
                click.echo(f"\n🚀 VPC 2.0 Networks ({len(vpc2s)}):")
                for vpc2 in vpc2s:
                    click.echo(f"   • {vpc2.get('description', 'unlabeled')} ({vpc2.get('id', 'N/A')})")
            
            if not vpcs and not vpc2s:
                click.echo("No VPC networks attached to this instance.")
            else:
                click.echo(f"\nTotal networks: {result['total_networks']}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_list_instance_networks())


@vpcs.command("info")
@click.argument("vpc_identifier")
@click.option("--vpc-type", type=click.Choice(["vpc", "vpc2", "auto"]), default="auto", help="Type of VPC")
@click.pass_context
def vpcs_info(ctx: click.Context, vpc_identifier: str, vpc_type: str):
    """Get comprehensive VPC information."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _get_network_info():
        from .server import VultrDNSServer
        from .vpcs import create_vpcs_mcp
        
        client = VultrDNSServer(api_key)
        mcp = create_vpcs_mcp(client)
        
        try:
            info = await mcp._tool_handlers["get_network_info"]["func"](vpc_identifier, vpc_type)
            
            network_type = info["network_type"]
            capabilities = info["capabilities"]
            
            click.echo(f"\n🌐 {network_type}: {info.get('description', 'unlabeled')}")
            click.echo("=" * 70)
            click.echo(f"ID: {info.get('id', 'N/A')}")
            click.echo(f"Region: {info.get('region', 'N/A')}")
            
            if network_type == "VPC":
                click.echo(f"Subnet: {info.get('v4_subnet', 'N/A')}/{info.get('v4_subnet_mask', 'N/A')}")
            else:
                click.echo(f"IP Block: {info.get('ip_block', 'N/A')}/{info.get('prefix_length', 'N/A')}")
            
            click.echo(f"Created: {info.get('date_created', 'N/A')}")
            
            click.echo(f"\n📊 Capabilities:")
            click.echo(f"   Scalability: {capabilities['scalability']}")
            click.echo(f"   Performance: {capabilities['performance']}")
            click.echo(f"   Max Instances: {capabilities['max_instances']}")
            click.echo(f"   Broadcast Traffic: {capabilities['broadcast_traffic']}")
            
            click.echo(f"\n💡 Recommendations:")
            for rec in info["recommendations"]:
                click.echo(f"   • {rec}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_get_network_info())


@cli.command()
@click.argument("domain")
@click.argument("ip")
@click.option("--include-www/--no-www", default=True, help="Include www subdomain")
@click.option("--ttl", type=int, help="TTL for records")
@click.pass_context
def setup_website(ctx: click.Context, domain: str, ip: str, include_www: bool, ttl: Optional[int]):
    """Set up basic DNS records for a website."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _setup_website():
        client = VultrDNSClient(api_key)
        try:
            result = await client.setup_basic_website(domain, ip, include_www, ttl)
            
            click.echo(f"Setting up website for {domain}:")
            
            for record in result['created_records']:
                click.echo(f"  ✅ {record}")
            
            for error in result['errors']:
                click.echo(f"  ❌ {error}")
            
            if result['created_records'] and not result['errors']:
                click.echo(f"🎉 Website setup complete for {domain}")
            elif result['errors']:
                click.echo(f"⚠️  Setup completed with some errors")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_setup_website())


@cli.command()
@click.argument("domain")
@click.argument("mail_server")
@click.option("--priority", default=10, help="MX record priority")
@click.option("--ttl", type=int, help="TTL for records")
@click.pass_context
def setup_email(ctx: click.Context, domain: str, mail_server: str, priority: int, ttl: Optional[int]):
    """Set up basic email DNS records."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _setup_email():
        client = VultrDNSClient(api_key)
        try:
            result = await client.setup_email(domain, mail_server, priority, ttl)
            
            click.echo(f"Setting up email for {domain}:")
            
            for record in result['created_records']:
                click.echo(f"  ✅ {record}")
            
            for error in result['errors']:
                click.echo(f"  ❌ {error}")
            
            if result['created_records'] and not result['errors']:
                click.echo(f"📧 Email setup complete for {domain}")
            elif result['errors']:
                click.echo(f"⚠️  Setup completed with some errors")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_setup_email())


# =============================================================================
# ISO Management Commands
# =============================================================================

@cli.group()
@click.pass_context
def iso(ctx: click.Context):
    """Manage ISO images."""
    pass


@iso.command("list")
@click.option("--filter", type=click.Choice(["all", "public", "custom"]), default="all", help="Filter ISOs")
@click.pass_context
def iso_list(ctx: click.Context, filter):
    """List ISO images."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _list_isos():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            if filter == "all":
                isos = await server.list_isos()
            elif filter == "public":
                all_isos = await server.list_isos()
                isos = [iso for iso in all_isos if not iso.get("filename")]
            else:  # custom
                all_isos = await server.list_isos()
                isos = [iso for iso in all_isos if iso.get("filename")]
            
            if not isos:
                click.echo(f"No {filter} ISOs found")
                return
            
            click.echo(f"Found {len(isos)} {filter} ISO(s):")
            for iso in isos:
                name = iso.get("name", "N/A")
                filename = iso.get("filename", "Public ISO")
                size = iso.get("size", "Unknown")
                click.echo(f"  • {name} - {filename} ({size} MB)")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_list_isos())


@iso.command("create")
@click.argument("url")
@click.pass_context
def iso_create(ctx: click.Context, url):
    """Create ISO from URL."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _create_iso():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            iso = await server.create_iso(url)
            click.echo(f"✅ ISO created: {iso.get('name', iso.get('id'))}")
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_create_iso())


# =============================================================================
# Operating System Commands
# =============================================================================

@cli.group()
@click.pass_context
def os(ctx: click.Context):
    """Manage operating systems."""
    pass


@os.command("list")
@click.option("--filter", type=click.Choice(["all", "linux", "windows", "apps"]), default="all", help="Filter OS types")
@click.pass_context
def os_list(ctx: click.Context, filter):
    """List operating systems."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _list_os():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            if filter == "all":
                operating_systems = await server.list_operating_systems()
            elif filter == "linux":
                all_os = await server.list_operating_systems()
                linux_keywords = ['ubuntu', 'debian', 'centos', 'fedora', 'arch', 'rocky', 'alma', 'opensuse']
                operating_systems = []
                for os_item in all_os:
                    name = os_item.get("name", "").lower()
                    if any(keyword in name for keyword in linux_keywords):
                        operating_systems.append(os_item)
            elif filter == "windows":
                all_os = await server.list_operating_systems()
                operating_systems = [os_item for os_item in all_os 
                                   if 'windows' in os_item.get("name", "").lower()]
            else:  # apps
                all_os = await server.list_operating_systems()
                operating_systems = [os_item for os_item in all_os 
                                   if os_item.get("family", "").lower() == "application"]
            
            if not operating_systems:
                click.echo(f"No {filter} operating systems found")
                return
            
            click.echo(f"Found {len(operating_systems)} {filter} operating system(s):")
            for os_item in operating_systems:
                name = os_item.get("name", "N/A")
                family = os_item.get("family", "N/A")
                arch = os_item.get("arch", "N/A")
                click.echo(f"  • {name} ({family}, {arch}) - ID: {os_item.get('id')}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_list_os())


# =============================================================================
# Plans Commands
# =============================================================================

@cli.group()
@click.pass_context
def plans(ctx: click.Context):
    """Manage hosting plans."""
    pass


@plans.command("list")
@click.option("--type", type=click.Choice(["all", "vc2", "vhf", "voc"]), default="all", help="Plan type filter")
@click.option("--min-vcpus", type=int, help="Minimum vCPUs")
@click.option("--min-ram", type=int, help="Minimum RAM (MB)")
@click.option("--max-cost", type=float, help="Maximum monthly cost")
@click.pass_context
def plans_list(ctx: click.Context, type, min_vcpus, min_ram, max_cost):
    """List hosting plans."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _list_plans():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            plan_type = None if type == "all" else type
            plans = await server.list_plans(plan_type)
            
            # Apply filters
            if min_vcpus or min_ram or max_cost:
                filtered_plans = []
                for plan in plans:
                    if min_vcpus and plan.get("vcpu_count", 0) < min_vcpus:
                        continue
                    if min_ram and plan.get("ram", 0) < min_ram:
                        continue
                    if max_cost and plan.get("monthly_cost", float('inf')) > max_cost:
                        continue
                    filtered_plans.append(plan)
                plans = filtered_plans
            
            if not plans:
                click.echo("No plans found matching criteria")
                return
            
            click.echo(f"Found {len(plans)} plan(s):")
            for plan in plans:
                name = plan.get("id", "N/A")
                vcpus = plan.get("vcpu_count", "N/A")
                ram = plan.get("ram", "N/A")
                disk = plan.get("disk", "N/A")
                cost = plan.get("monthly_cost", "N/A")
                click.echo(f"  • {name}: {vcpus} vCPU, {ram}MB RAM, {disk}GB disk - ${cost}/month")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_list_plans())


# =============================================================================
# Startup Scripts Commands
# =============================================================================

@cli.group()
@click.pass_context
def startup_scripts(ctx: click.Context):
    """Manage startup scripts."""
    pass


@startup_scripts.command("list")
@click.option("--type", type=click.Choice(["all", "boot", "pxe"]), default="all", help="Script type filter")
@click.pass_context
def startup_scripts_list(ctx: click.Context, type):
    """List startup scripts."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _list_scripts():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            all_scripts = await server.list_startup_scripts()
            
            if type != "all":
                scripts = [script for script in all_scripts 
                          if script.get("type", "").lower() == type]
            else:
                scripts = all_scripts
            
            if not scripts:
                click.echo(f"No {type} startup scripts found")
                return
            
            click.echo(f"Found {len(scripts)} {type} startup script(s):")
            for script in scripts:
                name = script.get("name", "N/A")
                script_type = script.get("type", "N/A")
                created = script.get("date_created", "N/A")
                click.echo(f"  • {name} ({script_type}) - Created: {created}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_list_scripts())


@startup_scripts.command("create")
@click.argument("name")
@click.argument("script_content")
@click.option("--type", type=click.Choice(["boot", "pxe"]), default="boot", help="Script type")
@click.pass_context
def startup_scripts_create(ctx: click.Context, name, script_content, type):
    """Create a startup script."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _create_script():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            script = await server.create_startup_script(name, script_content, type)
            click.echo(f"✅ Startup script created: {script.get('name')} (ID: {script.get('id')})")
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_create_script())


@startup_scripts.command("delete")
@click.argument("script_name")
@click.pass_context
def startup_scripts_delete(ctx: click.Context, script_name):
    """Delete a startup script by name."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _delete_script():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            # Find script by name
            scripts = await server.list_startup_scripts()
            script_id = None
            for script in scripts:
                if script.get("name") == script_name:
                    script_id = script["id"]
                    break
            
            if not script_id:
                click.echo(f"Startup script '{script_name}' not found", err=True)
                sys.exit(1)
            
            await server.delete_startup_script(script_id)
            click.echo(f"✅ Startup script '{script_name}' deleted")
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_delete_script())


# =============================================================================
# Billing Commands
# =============================================================================

@cli.group()
@click.pass_context
def billing(ctx: click.Context):
    """Manage billing and account information."""
    pass


@billing.command("account")
@click.pass_context
def billing_account(ctx: click.Context):
    """Show account information and current balance."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _show_account():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            account = await server.get_account_info()
            balance = await server.get_current_balance()
            
            click.echo("Account Information:")
            click.echo(f"  Name: {account.get('name', 'N/A')}")
            click.echo(f"  Email: {account.get('email', 'N/A')}")
            click.echo(f"  Current Balance: ${balance.get('balance', 0):.2f}")
            click.echo(f"  Pending Charges: ${balance.get('pending_charges', 0):.2f}")
            
            if balance.get('last_payment_date'):
                click.echo(f"  Last Payment: ${balance.get('last_payment_amount', 0):.2f} on {balance.get('last_payment_date')}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_show_account())


@billing.command("history")
@click.option("--days", type=int, default=30, help="Number of days to include")
@click.option("--limit", type=int, default=25, help="Number of items to show")
@click.pass_context
def billing_history(ctx: click.Context, days, limit):
    """Show billing history."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _show_history():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            history = await server.list_billing_history(date_range=days, per_page=limit)
            billing_items = history.get("billing_history", [])
            
            if not billing_items:
                click.echo(f"No billing history found for the last {days} days")
                return
            
            click.echo(f"Billing History (last {days} days):")
            total_cost = 0
            
            for item in billing_items:
                date = item.get("date", "Unknown")
                amount = float(item.get("amount", 0))
                description = item.get("description", "N/A")
                total_cost += amount
                
                click.echo(f"  {date}: ${amount:.2f} - {description}")
            
            click.echo(f"\nTotal for period: ${total_cost:.2f}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_show_history())


@billing.command("invoices")
@click.option("--limit", type=int, default=10, help="Number of invoices to show")
@click.pass_context
def billing_invoices(ctx: click.Context, limit):
    """List invoices."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _list_invoices():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            invoices_data = await server.list_invoices(per_page=limit)
            invoices = invoices_data.get("billing_invoices", [])
            
            if not invoices:
                click.echo("No invoices found")
                return
            
            click.echo(f"Recent Invoices:")
            for invoice in invoices:
                invoice_id = invoice.get("id", "N/A")
                date = invoice.get("date", "Unknown")
                amount = invoice.get("amount", "N/A")
                status = invoice.get("status", "Unknown")
                
                click.echo(f"  {invoice_id}: ${amount} - {date} ({status})")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_list_invoices())


@billing.command("monthly")
@click.option("--year", type=int, help="Year (e.g., 2024)")
@click.option("--month", type=int, help="Month (1-12)")
@click.pass_context
def billing_monthly(ctx: click.Context, year, month):
    """Show monthly usage summary."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    # Default to current month if not specified
    if not year or not month:
        from datetime import datetime
        now = datetime.now()
        year = year or now.year
        month = month or now.month
    
    async def _show_monthly():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            summary = await server.get_monthly_usage_summary(year, month)
            
            click.echo(f"Monthly Summary for {month}/{year}:")
            click.echo(f"  Total Cost: ${summary.get('total_cost', 0):.2f}")
            click.echo(f"  Transactions: {summary.get('transaction_count', 0)}")
            click.echo(f"  Average Daily Cost: ${summary.get('average_daily_cost', 0):.2f}")
            
            services = summary.get('service_breakdown', {})
            if services:
                click.echo("\n  Service Breakdown:")
                for service, cost in services.items():
                    click.echo(f"    {service}: ${cost:.2f}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_show_monthly())


@billing.command("trends")
@click.option("--months", type=int, default=6, help="Number of months to analyze")
@click.pass_context
def billing_trends(ctx: click.Context, months):
    """Analyze spending trends."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _analyze_trends():
        from .server import VultrDNSServer
        from .billing import create_billing_mcp
        server = VultrDNSServer(api_key)
        billing_mcp = create_billing_mcp(server)
        
        try:
            # Access the analyze_spending_trends tool directly
            analysis = await server.get_monthly_usage_summary(2024, 1)  # Placeholder - we'd need to implement this properly
            
            # For now, show a simple version
            current_summary = await server.get_monthly_usage_summary(2024, 1)
            
            click.echo(f"Spending Trends Analysis ({months} months):")
            click.echo("  Feature coming soon - advanced trend analysis")
            click.echo(f"  Current month estimate: ${current_summary.get('total_cost', 0):.2f}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_analyze_trends())


# =============================================================================
# Bare Metal Commands
# =============================================================================

@cli.group()
@click.pass_context
def bare_metal(ctx: click.Context):
    """Manage bare metal servers."""
    pass


@bare_metal.command("list")
@click.option("--status", help="Filter by status (active, stopped, installing)")
@click.option("--region", help="Filter by region")
@click.pass_context
def bare_metal_list(ctx: click.Context, status, region):
    """List bare metal servers."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _list_servers():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            servers = await server.list_bare_metal_servers()
            
            # Apply filters
            if status:
                servers = [s for s in servers if s.get("status", "").lower() == status.lower()]
            if region:
                servers = [s for s in servers if s.get("region") == region]
            
            if not servers:
                click.echo("No bare metal servers found")
                return
            
            click.echo(f"Found {len(servers)} bare metal server(s):")
            for srv in servers:
                label = srv.get("label", "N/A")
                status_val = srv.get("status", "Unknown")
                plan = srv.get("plan", "N/A")
                region_val = srv.get("region", "N/A")
                ip = srv.get("main_ip", "N/A")
                click.echo(f"  • {label} ({status_val}) - {plan} in {region_val} - IP: {ip}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_list_servers())


@bare_metal.command("get")
@click.argument("server_name")
@click.pass_context
def bare_metal_get(ctx: click.Context, server_name):
    """Get bare metal server details by name or ID."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _get_server():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            # Find server by name/label first
            servers = await server.list_bare_metal_servers()
            server_id = None
            
            for srv in servers:
                if (srv.get("label") == server_name or 
                    srv.get("hostname") == server_name or
                    srv.get("id") == server_name):
                    server_id = srv["id"]
                    break
            
            if not server_id:
                click.echo(f"Bare metal server '{server_name}' not found", err=True)
                sys.exit(1)
            
            server_info = await server.get_bare_metal_server(server_id)
            
            click.echo(f"Bare Metal Server: {server_info.get('label', 'N/A')}")
            click.echo(f"  ID: {server_info.get('id', 'N/A')}")
            click.echo(f"  Status: {server_info.get('status', 'Unknown')}")
            click.echo(f"  Plan: {server_info.get('plan', 'N/A')}")
            click.echo(f"  Region: {server_info.get('region', 'N/A')}")
            click.echo(f"  OS: {server_info.get('os', 'N/A')}")
            click.echo(f"  RAM: {server_info.get('ram', 'N/A')} MB")
            click.echo(f"  CPU: {server_info.get('vcpu_count', 'N/A')} cores")
            click.echo(f"  Main IP: {server_info.get('main_ip', 'N/A')}")
            click.echo(f"  Hostname: {server_info.get('hostname', 'N/A')}")
            click.echo(f"  Monthly Cost: ${server_info.get('cost_per_month', 'N/A')}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_get_server())


@bare_metal.command("create")
@click.argument("region")
@click.argument("plan")
@click.option("--os-id", help="Operating system ID")
@click.option("--iso-id", help="ISO ID for custom installation")
@click.option("--label", help="Server label")
@click.option("--hostname", help="Server hostname")
@click.option("--ssh-keys", help="Comma-separated SSH key IDs")
@click.option("--enable-ipv6", is_flag=True, help="Enable IPv6")
@click.option("--enable-ddos", is_flag=True, help="Enable DDoS protection")
@click.pass_context
def bare_metal_create(ctx: click.Context, region, plan, os_id, iso_id, label, hostname, ssh_keys, enable_ipv6, enable_ddos):
    """Create a new bare metal server."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _create_server():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            ssh_key_list = ssh_keys.split(",") if ssh_keys else None
            
            new_server = await server.create_bare_metal_server(
                region=region,
                plan=plan,
                os_id=os_id,
                iso_id=iso_id,
                label=label,
                hostname=hostname,
                ssh_key_ids=ssh_key_list,
                enable_ipv6=enable_ipv6,
                enable_ddos_protection=enable_ddos
            )
            
            click.echo(f"✅ Bare metal server created:")
            click.echo(f"  ID: {new_server.get('id')}")
            click.echo(f"  Label: {new_server.get('label', 'N/A')}")
            click.echo(f"  Status: {new_server.get('status', 'Unknown')}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_create_server())


@bare_metal.command("start")
@click.argument("server_name")
@click.pass_context
def bare_metal_start(ctx: click.Context, server_name):
    """Start a bare metal server."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _start_server():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            # Find server by name/label first
            servers = await server.list_bare_metal_servers()
            server_id = None
            
            for srv in servers:
                if (srv.get("label") == server_name or 
                    srv.get("hostname") == server_name or
                    srv.get("id") == server_name):
                    server_id = srv["id"]
                    break
            
            if not server_id:
                click.echo(f"Bare metal server '{server_name}' not found", err=True)
                sys.exit(1)
            
            await server.start_bare_metal_server(server_id)
            click.echo(f"✅ Started bare metal server '{server_name}'")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_start_server())


@bare_metal.command("stop")
@click.argument("server_name")
@click.pass_context
def bare_metal_stop(ctx: click.Context, server_name):
    """Stop a bare metal server."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _stop_server():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            # Find server by name/label first
            servers = await server.list_bare_metal_servers()
            server_id = None
            
            for srv in servers:
                if (srv.get("label") == server_name or 
                    srv.get("hostname") == server_name or
                    srv.get("id") == server_name):
                    server_id = srv["id"]
                    break
            
            if not server_id:
                click.echo(f"Bare metal server '{server_name}' not found", err=True)
                sys.exit(1)
            
            await server.stop_bare_metal_server(server_id)
            click.echo(f"✅ Stopped bare metal server '{server_name}'")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_stop_server())


@bare_metal.command("reboot")
@click.argument("server_name")
@click.pass_context
def bare_metal_reboot(ctx: click.Context, server_name):
    """Reboot a bare metal server."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _reboot_server():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            # Find server by name/label first
            servers = await server.list_bare_metal_servers()
            server_id = None
            
            for srv in servers:
                if (srv.get("label") == server_name or 
                    srv.get("hostname") == server_name or
                    srv.get("id") == server_name):
                    server_id = srv["id"]
                    break
            
            if not server_id:
                click.echo(f"Bare metal server '{server_name}' not found", err=True)
                sys.exit(1)
            
            await server.reboot_bare_metal_server(server_id)
            click.echo(f"✅ Rebooted bare metal server '{server_name}'")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_reboot_server())


@bare_metal.command("plans")
@click.option("--type", help="Plan type filter")
@click.option("--min-vcpus", type=int, help="Minimum vCPUs")
@click.option("--min-ram", type=int, help="Minimum RAM (GB)")
@click.option("--max-cost", type=float, help="Maximum monthly cost")
@click.pass_context
def bare_metal_plans(ctx: click.Context, type, min_vcpus, min_ram, max_cost):
    """List bare metal plans."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _list_plans():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            plans = await server.list_bare_metal_plans(type)
            
            # Apply filters
            if min_vcpus or min_ram or max_cost:
                filtered_plans = []
                for plan in plans:
                    if min_vcpus and plan.get("vcpu_count", 0) < min_vcpus:
                        continue
                    if min_ram and plan.get("ram", 0) < min_ram * 1024:  # Convert GB to MB
                        continue
                    if max_cost and plan.get("monthly_cost", float('inf')) > max_cost:
                        continue
                    filtered_plans.append(plan)
                plans = filtered_plans
            
            if not plans:
                click.echo("No bare metal plans found matching criteria")
                return
            
            click.echo(f"Found {len(plans)} bare metal plan(s):")
            for plan in plans:
                plan_id = plan.get("id", "N/A")
                vcpus = plan.get("vcpu_count", "N/A")
                ram_gb = plan.get("ram", 0) // 1024 if plan.get("ram") else "N/A"
                disk = plan.get("disk", "N/A")
                cost = plan.get("monthly_cost", "N/A")
                click.echo(f"  • {plan_id}: {vcpus} vCPU, {ram_gb}GB RAM, {disk}GB disk - ${cost}/month")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_list_plans())


# =============================================================================
# CDN Commands
# =============================================================================

@cli.group()
@click.pass_context
def cdn(ctx: click.Context):
    """Manage CDN zones."""
    pass


@cdn.command("list")
@click.pass_context
def cdn_list(ctx: click.Context):
    """List CDN zones."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _list_zones():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            zones = await server.list_cdn_zones()
            
            if not zones:
                click.echo("No CDN zones found")
                return
            
            click.echo(f"Found {len(zones)} CDN zone(s):")
            for zone in zones:
                origin = zone.get("origin_domain", "N/A")
                cdn_domain = zone.get("cdn_domain", "N/A")
                status = zone.get("status", "Unknown")
                regions = len(zone.get("regions", []))
                click.echo(f"  • {origin} -> {cdn_domain} ({status}) - {regions} regions")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_list_zones())


@cdn.command("get")
@click.argument("domain")
@click.pass_context
def cdn_get(ctx: click.Context, domain):
    """Get CDN zone details by origin domain or CDN domain."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _get_zone():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            # Find zone by domain
            zones = await server.list_cdn_zones()
            zone_id = None
            
            for zone in zones:
                if (zone.get("origin_domain") == domain or 
                    zone.get("cdn_domain") == domain or
                    zone.get("id") == domain):
                    zone_id = zone["id"]
                    break
            
            if not zone_id:
                click.echo(f"CDN zone for domain '{domain}' not found", err=True)
                sys.exit(1)
            
            zone_info = await server.get_cdn_zone(zone_id)
            
            click.echo(f"CDN Zone: {zone_info.get('origin_domain', 'N/A')}")
            click.echo(f"  ID: {zone_info.get('id', 'N/A')}")
            click.echo(f"  CDN Domain: {zone_info.get('cdn_domain', 'N/A')}")
            click.echo(f"  Status: {zone_info.get('status', 'Unknown')}")
            click.echo(f"  Origin Scheme: {zone_info.get('origin_scheme', 'N/A')}")
            click.echo(f"  Gzip Compression: {zone_info.get('gzip_compression', False)}")
            click.echo(f"  Block Bad Bots: {zone_info.get('block_bad_bots', False)}")
            click.echo(f"  Block AI Bots: {zone_info.get('block_ai_bots', False)}")
            click.echo(f"  Regions: {', '.join(zone_info.get('regions', []))}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_get_zone())


@cdn.command("create")
@click.argument("origin_domain")
@click.option("--scheme", type=click.Choice(["http", "https"]), default="https", help="Origin scheme")
@click.option("--gzip", is_flag=True, help="Enable gzip compression")
@click.option("--block-bots", is_flag=True, help="Enable bot blocking")
@click.option("--regions", help="Comma-separated list of regions")
@click.pass_context
def cdn_create(ctx: click.Context, origin_domain, scheme, gzip, block_bots, regions):
    """Create a new CDN zone."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _create_zone():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            region_list = regions.split(",") if regions else None
            
            new_zone = await server.create_cdn_zone(
                origin_domain=origin_domain,
                origin_scheme=scheme,
                gzip_compression=gzip,
                block_ai_bots=block_bots,
                block_bad_bots=block_bots,
                regions=region_list
            )
            
            click.echo(f"✅ CDN zone created:")
            click.echo(f"  Origin Domain: {new_zone.get('origin_domain')}")
            click.echo(f"  CDN Domain: {new_zone.get('cdn_domain')}")
            click.echo(f"  Status: {new_zone.get('status', 'Unknown')}")
            click.echo(f"  ID: {new_zone.get('id')}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_create_zone())


@cdn.command("purge")
@click.argument("domain")
@click.pass_context
def cdn_purge(ctx: click.Context, domain):
    """Purge CDN zone cache."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _purge_zone():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            # Find zone by domain
            zones = await server.list_cdn_zones()
            zone_id = None
            
            for zone in zones:
                if (zone.get("origin_domain") == domain or 
                    zone.get("cdn_domain") == domain or
                    zone.get("id") == domain):
                    zone_id = zone["id"]
                    break
            
            if not zone_id:
                click.echo(f"CDN zone for domain '{domain}' not found", err=True)
                sys.exit(1)
            
            await server.purge_cdn_zone(zone_id)
            click.echo(f"✅ Purged CDN cache for {domain}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_purge_zone())


@cdn.command("stats")
@click.argument("domain")
@click.pass_context
def cdn_stats(ctx: click.Context, domain):
    """Show CDN zone statistics."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _show_stats():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            # Find zone by domain
            zones = await server.list_cdn_zones()
            zone_id = None
            
            for zone in zones:
                if (zone.get("origin_domain") == domain or 
                    zone.get("cdn_domain") == domain or
                    zone.get("id") == domain):
                    zone_id = zone["id"]
                    break
            
            if not zone_id:
                click.echo(f"CDN zone for domain '{domain}' not found", err=True)
                sys.exit(1)
            
            stats = await server.get_cdn_zone_stats(zone_id)
            
            click.echo(f"CDN Statistics for {domain}:")
            click.echo(f"  Total Requests: {stats.get('total_requests', 'N/A')}")
            click.echo(f"  Cache Hits: {stats.get('cache_hits', 'N/A')}")
            click.echo(f"  Bandwidth Used: {stats.get('bandwidth_bytes', 'N/A')} bytes")
            
            # Calculate cache hit ratio
            total_requests = stats.get('total_requests', 0)
            cache_hits = stats.get('cache_hits', 0)
            if total_requests > 0:
                hit_ratio = (cache_hits / total_requests) * 100
                click.echo(f"  Cache Hit Ratio: {hit_ratio:.1f}%")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_show_stats())


@cdn.command("regions")
@click.pass_context
def cdn_regions(ctx: click.Context):
    """List available CDN regions."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _list_regions():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            regions = await server.get_cdn_available_regions()
            
            if not regions:
                click.echo("No CDN regions found")
                return
            
            click.echo(f"Available CDN Regions ({len(regions)}):")
            for region in regions:
                region_id = region.get("id", "N/A")
                name = region.get("name", "N/A")
                country = region.get("country", "N/A")
                click.echo(f"  • {region_id}: {name} ({country})")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_list_regions())


# =============================================================================
# Kubernetes Commands
# =============================================================================

@cli.group()
@click.pass_context
def kubernetes(ctx: click.Context):
    """Manage Kubernetes clusters."""
    pass


@kubernetes.command("list")
@click.pass_context
def kubernetes_list(ctx: click.Context):
    """List Kubernetes clusters."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _list_clusters():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            clusters = await server.list_kubernetes_clusters()
            
            if not clusters:
                click.echo("No Kubernetes clusters found")
                return
            
            click.echo(f"Kubernetes Clusters ({len(clusters)}):")
            for cluster in clusters:
                cluster_id = cluster.get("id", "N/A")
                label = cluster.get("label", "N/A")
                status = cluster.get("status", "N/A")
                region = cluster.get("region", "N/A")
                version = cluster.get("version", "N/A")
                node_pools = cluster.get("node_pools", 0)
                click.echo(f"  • {label} ({cluster_id[:8]}...)")
                click.echo(f"    Status: {status} | Region: {region} | Version: {version}")
                click.echo(f"    Node Pools: {node_pools}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_list_clusters())


@kubernetes.command("get")
@click.argument("cluster_name")
@click.pass_context
def kubernetes_get(ctx: click.Context, cluster_name):
    """Get Kubernetes cluster details."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _get_cluster():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            clusters = await server.list_kubernetes_clusters()
            cluster = None
            
            for c in clusters:
                if (c.get("label") == cluster_name or 
                    c.get("id") == cluster_name):
                    cluster = c
                    break
            
            if not cluster:
                click.echo(f"Kubernetes cluster '{cluster_name}' not found", err=True)
                sys.exit(1)
            
            click.echo(f"Kubernetes Cluster: {cluster.get('label')}")
            click.echo(f"  ID: {cluster.get('id')}")
            click.echo(f"  Status: {cluster.get('status')}")
            click.echo(f"  Region: {cluster.get('region')}")
            click.echo(f"  Version: {cluster.get('version')}")
            click.echo(f"  Endpoint: {cluster.get('endpoint', 'N/A')}")
            click.echo(f"  Node Pools: {cluster.get('node_pools', 0)}")
            click.echo(f"  Created: {cluster.get('date_created', 'N/A')}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_get_cluster())


# =============================================================================
# Load Balancer Commands
# =============================================================================

@cli.group()
@click.pass_context
def load_balancer(ctx: click.Context):
    """Manage load balancers."""
    pass


@load_balancer.command("list")
@click.pass_context
def load_balancer_list(ctx: click.Context):
    """List load balancers."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _list_load_balancers():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            load_balancers = await server.list_load_balancers()
            
            if not load_balancers:
                click.echo("No load balancers found")
                return
            
            click.echo(f"Load Balancers ({len(load_balancers)}):")
            for lb in load_balancers:
                lb_id = lb.get("id", "N/A")
                label = lb.get("label", "N/A")
                status = lb.get("status", "N/A")
                region = lb.get("region", "N/A")
                ip_v4 = lb.get("ipv4", "N/A")
                click.echo(f"  • {label} ({lb_id[:8]}...)")
                click.echo(f"    Status: {status} | Region: {region} | IP: {ip_v4}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_list_load_balancers())


# =============================================================================
# Database Commands
# =============================================================================

@cli.group()
@click.pass_context
def databases(ctx: click.Context):
    """Manage managed databases."""
    pass


@databases.command("list")
@click.option("--engine", help="Filter by database engine (mysql, pg, redis)")
@click.pass_context
def databases_list(ctx: click.Context, engine):
    """List managed databases."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _list_databases():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            databases = await server.list_managed_databases()
            
            if engine:
                databases = [db for db in databases if db.get("database_engine") == engine]
            
            if not databases:
                engine_text = f" ({engine})" if engine else ""
                click.echo(f"No managed databases found{engine_text}")
                return
            
            click.echo(f"Managed Databases ({len(databases)}):")
            for db in databases:
                db_id = db.get("id", "N/A")
                label = db.get("label", "N/A")
                engine_type = db.get("database_engine", "N/A")
                status = db.get("status", "N/A")
                region = db.get("region", "N/A")
                plan = db.get("plan", "N/A")
                click.echo(f"  • {label} ({db_id[:8]}...)")
                click.echo(f"    Engine: {engine_type} | Status: {status} | Region: {region}")
                click.echo(f"    Plan: {plan}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_list_databases())


# =============================================================================
# Object Storage Commands
# =============================================================================

@cli.group()
@click.pass_context
def object_storage(ctx: click.Context):
    """Manage object storage."""
    pass


@object_storage.command("list")
@click.pass_context
def object_storage_list(ctx: click.Context):
    """List object storage instances."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _list_storage():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            storage = await server.list_object_storage()
            
            if not storage:
                click.echo("No object storage instances found")
                return
            
            click.echo(f"Object Storage Instances ({len(storage)}):")
            for s in storage:
                s_id = s.get("id", "N/A")
                label = s.get("label", "N/A")
                status = s.get("status", "N/A")
                cluster_id = s.get("cluster_id", "N/A")
                s3_hostname = s.get("s3_hostname", "N/A")
                click.echo(f"  • {label} ({s_id[:8]}...)")
                click.echo(f"    Status: {status} | Cluster: {cluster_id}")
                click.echo(f"    S3 Endpoint: {s3_hostname}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_list_storage())


# =============================================================================
# Users Commands
# =============================================================================

@cli.group()
@click.pass_context
def users(ctx: click.Context):
    """Manage users."""
    pass


@users.command("list")
@click.pass_context
def users_list(ctx: click.Context):
    """List users."""
    api_key = ctx.obj.get('api_key')
    if not api_key:
        click.echo("Error: VULTR_API_KEY is required", err=True)
        sys.exit(1)
    
    async def _list_users():
        from .server import VultrDNSServer
        server = VultrDNSServer(api_key)
        try:
            users = await server.list_users()
            
            if not users:
                click.echo("No users found")
                return
            
            click.echo(f"Users ({len(users)}):")
            for user in users:
                user_id = user.get("id", "N/A")
                name = user.get("name", "N/A")
                email = user.get("email", "N/A")
                acls = user.get("acls", [])
                click.echo(f"  • {name} ({email})")
                click.echo(f"    ID: {user_id}")
                click.echo(f"    Permissions: {', '.join(acls) if acls else 'None'}")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_list_users())


def main():
    """Main entry point for the CLI."""
    cli()


def server_command():
    """Entry point for the server command."""
    cli(['server'])


if __name__ == "__main__":
    main()
