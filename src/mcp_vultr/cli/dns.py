"""
DNS commands for mcp-vultr CLI.

This module contains all DNS-related commands including domain and record management.
"""

import sys

import click
from rich.table import Table

from ..client import VultrDNSClient
from .utils import console, handle_api_key_error, run_async_command


@click.group()
@click.pass_context
def domains(ctx: click.Context):
    """Manage DNS domains."""
    pass


@domains.command("list")
@click.pass_context
def list_domains(ctx: click.Context):
    """List all domains in your account."""
    api_key = handle_api_key_error(ctx.obj.get("api_key"))

    async def _list_domains():
        client = VultrDNSClient(api_key)
        with console.status("[bold green]Fetching domains..."):
            domains_list = await client.domains()

        if not domains_list:
            console.print("[yellow]No domains found[/yellow]")
            return

        # Create a beautiful table
        table = Table(
            title=f"[bold blue]Vultr DNS Domains ({len(domains_list)} found)[/bold blue]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Domain", style="cyan", no_wrap=True)
        table.add_column("Created", style="green")
        table.add_column("DNSSEC", style="yellow")

        for domain in domains_list:
            domain_name = domain.get("domain", "Unknown")
            created = domain.get("date_created", "Unknown")
            dnssec = domain.get("dns_sec", "disabled")

            table.add_row(
                domain_name,
                created,
                "✅ enabled" if dnssec == "enabled" else "❌ disabled",
            )

        console.print(table)

    run_async_command(_list_domains)


@domains.command("info")
@click.argument("domain")
@click.pass_context
def domain_info(ctx: click.Context, domain: str):
    """Get detailed information about a domain."""
    api_key = handle_api_key_error(ctx.obj.get("api_key"))

    async def _domain_info():
        client = VultrDNSClient(api_key)
        summary = await client.get_domain_summary(domain)

        if "error" in summary:
            console.print(f"[red]Error: {summary['error']}[/red]")
            sys.exit(1)

        console.print(f"[bold blue]Domain: {domain}[/bold blue]")
        console.print(f"Total Records: {summary['total_records']}")

        if summary["record_types"]:
            console.print("Record Types:")
            for record_type, count in summary["record_types"].items():
                console.print(f"  • {record_type}: {count}")

        config = summary["configuration"]
        console.print("Configuration:")
        console.print(
            f"  • Root domain record: {'✅' if config['has_root_record'] else '❌'}"
        )
        console.print(
            f"  • WWW subdomain: {'✅' if config['has_www_subdomain'] else '❌'}"
        )
        console.print(f"  • Email setup: {'✅' if config['has_email_setup'] else '❌'}")

    run_async_command(_domain_info)


@domains.command("create")
@click.argument("domain")
@click.argument("ip")
@click.pass_context
def create_domain(ctx: click.Context, domain: str, ip: str):
    """Create a new domain with default A record."""
    api_key = handle_api_key_error(ctx.obj.get("api_key"))

    async def _create_domain():
        client = VultrDNSClient(api_key)
        result = await client.add_domain(domain, ip)

        if "error" in result:
            console.print(f"[red]Error creating domain: {result['error']}[/red]")
            sys.exit(1)

        console.print(f"[green]✅ Created domain {domain} with IP {ip}[/green]")

    run_async_command(_create_domain)


@click.group()
@click.pass_context
def records(ctx: click.Context):
    """Manage DNS records."""
    pass


@records.command("list")
@click.argument("domain")
@click.option("--type", "record_type", help="Filter by record type")
@click.pass_context
def list_records(ctx: click.Context, domain: str, record_type: str | None):
    """List DNS records for a domain."""
    api_key = handle_api_key_error(ctx.obj.get("api_key"))

    async def _list_records():
        client = VultrDNSClient(api_key)
        if record_type:
            records_list = await client.find_records_by_type(domain, record_type)
        else:
            records_list = await client.records(domain)

        if not records_list:
            console.print(f"[yellow]No records found for {domain}[/yellow]")
            return

        console.print(f"[bold blue]DNS records for {domain}:[/bold blue]")
        for record in records_list:
            record_id = record.get("id", "Unknown")
            r_type = record.get("type", "Unknown")
            name = record.get("name", "Unknown")
            data = record.get("data", "Unknown")
            ttl = record.get("ttl", "Unknown")

            console.print(
                f"  • [{record_id}] {r_type:6} {name:20} ➜ {data} (TTL: {ttl})"
            )

    run_async_command(_list_records)


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
    ttl: int | None,
    priority: int | None,
):
    """Add a new DNS record."""
    api_key = handle_api_key_error(ctx.obj.get("api_key"))

    async def _add_record():
        client = VultrDNSClient(api_key)
        result = await client.add_record(
            domain, record_type, name, value, ttl, priority
        )

        if "error" in result:
            console.print(f"[red]Error creating record: {result['error']}[/red]")
            sys.exit(1)

        record_id = result.get("id", "Unknown")
        console.print(
            f"[green]✅ Created {record_type} record [{record_id}]: {name} ➜ {value}[/green]"
        )

    run_async_command(_add_record)


@records.command("delete")
@click.argument("domain")
@click.argument("record_id")
@click.confirmation_option(prompt="Are you sure you want to delete this record?")
@click.pass_context
def delete_record(ctx: click.Context, domain: str, record_id: str):
    """Delete a DNS record."""
    api_key = handle_api_key_error(ctx.obj.get("api_key"))

    async def _delete_record():
        client = VultrDNSClient(api_key)
        success = await client.remove_record(domain, record_id)

        if success:
            console.print(f"[green]✅ Deleted record {record_id}[/green]")
        else:
            console.print(f"[red]❌ Failed to delete record {record_id}[/red]")
            sys.exit(1)

    run_async_command(_delete_record)


@click.command("setup-website")
@click.argument("domain")
@click.argument("ip")
@click.option("--no-www", is_flag=True, help="Skip creating www subdomain")
@click.option("--ttl", type=int, help="TTL for records in seconds")
@click.pass_context
def setup_website(
    ctx: click.Context, domain: str, ip: str, no_www: bool, ttl: int | None
):
    """Set up basic DNS records for a website."""
    api_key = handle_api_key_error(ctx.obj.get("api_key"))

    async def _setup_website():
        client = VultrDNSClient(api_key)
        console.print(
            f"[bold green]Setting up website DNS for {domain}...[/bold green]"
        )

        result = await client.setup_basic_website(
            domain, ip, include_www=not no_www, ttl=ttl
        )

        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            sys.exit(1)

        console.print(f"[green]✅ Website setup complete for {domain}[/green]")

        if result.get("created_records"):
            console.print("[bold]Created records:[/bold]")
            for record in result["created_records"]:
                console.print(f"  • {record}")

        if result.get("errors"):
            console.print("[yellow]Setup completed with some errors:[/yellow]")
            for error in result["errors"]:
                console.print(f"  • {error}")

    run_async_command(_setup_website)


@click.command("setup-email")
@click.argument("domain")
@click.argument("mail_server")
@click.option(
    "--priority", type=int, default=10, help="MX record priority (default: 10)"
)
@click.option("--ttl", type=int, help="TTL for records in seconds")
@click.pass_context
def setup_email(
    ctx: click.Context, domain: str, mail_server: str, priority: int, ttl: int | None
):
    """Set up basic email DNS records."""
    api_key = handle_api_key_error(ctx.obj.get("api_key"))

    async def _setup_email():
        client = VultrDNSClient(api_key)
        console.print(f"[bold green]Setting up email DNS for {domain}...[/bold green]")

        result = await client.setup_email(
            domain, mail_server, priority=priority, ttl=ttl
        )

        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            sys.exit(1)

        console.print(f"[green]✅ Email setup complete for {domain}[/green]")

        if result.get("created_records"):
            console.print("[bold]Created records:[/bold]")
            for record in result["created_records"]:
                console.print(f"  • {record}")

        if result.get("skipped_records"):
            console.print("[yellow]Skipped (already exist):[/yellow]")
            for record in result["skipped_records"]:
                console.print(f"  • {record}")

    run_async_command(_setup_email)
