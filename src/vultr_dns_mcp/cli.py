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


def main():
    """Main entry point for the CLI."""
    cli()


def server_command():
    """Entry point for the server command."""
    cli(['server'])


if __name__ == "__main__":
    main()
