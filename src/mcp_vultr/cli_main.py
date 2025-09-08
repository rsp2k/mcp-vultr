"""
Refactored Command Line Interface for Vultr DNS MCP.

This module provides a modular CLI with commands organized by service area.
"""

import sys

import click

from ._version import __version__
from .cli.utils import console
from .server import run_server


@click.group()
@click.version_option(__version__)
@click.option(
    "--api-key",
    envvar="VULTR_API_KEY",
    help="Vultr API key (or set VULTR_API_KEY environment variable)",
)
@click.pass_context
def cli(ctx: click.Context, api_key: str | None):
    """Vultr DNS MCP - Manage Vultr DNS through Model Context Protocol."""
    ctx.ensure_object(dict)
    ctx.obj["api_key"] = api_key


@cli.command()
@click.pass_context
def server(ctx: click.Context):
    """Start the Vultr DNS MCP server."""
    api_key = ctx.obj.get("api_key")

    if not api_key:
        console.print("[red]Error: VULTR_API_KEY is required[/red]")
        console.print(
            "[yellow]Set it as an environment variable or use --api-key option[/yellow]"
        )
        sys.exit(1)

    try:
        console.print("[bold green]Starting Vultr DNS MCP Server...[/bold green]")
        console.print("[dim]Press Ctrl+C to stop[/dim]")
        run_server(api_key)
    except Exception as e:
        console.print(f"[red]Error starting server: {e}[/red]")
        sys.exit(1)


# Register command groups from modules
def register_commands():
    """Register all command groups from refactored modules."""
    # Import and register DNS commands
    from .cli.dns import domains, records

    cli.add_command(domains)
    cli.add_command(records)

    # Import and register billing commands
    from .cli.billing import billing

    cli.add_command(billing)

    # Import and register compute commands
    from .cli.compute import bare_metal, operating_systems, plans, startup_scripts

    cli.add_command(operating_systems)
    cli.add_command(plans)
    cli.add_command(startup_scripts)
    cli.add_command(bare_metal)

    # Add placeholder groups for remaining services
    # These will be implemented in future iterations

    @cli.group()
    def container_registry():
        """Manage Vultr container registries."""
        console.print("[yellow]Container registry commands coming soon![/yellow]")

    @cli.group()
    def block_storage():
        """Manage Vultr block storage volumes."""
        console.print("[yellow]Block storage commands coming soon![/yellow]")

    @cli.group()
    def vpcs():
        """Manage Vultr VPCs and VPC 2.0 networks."""
        console.print("[yellow]VPC commands coming soon![/yellow]")

    @cli.group()
    def iso():
        """Manage ISO images."""
        console.print("[yellow]ISO commands coming soon![/yellow]")

    @cli.group()
    def cdn():
        """Manage CDN zones."""
        console.print("[yellow]CDN commands coming soon![/yellow]")

    @cli.group()
    def kubernetes():
        """Manage Kubernetes clusters."""
        console.print("[yellow]Kubernetes commands coming soon![/yellow]")

    @cli.group()
    def load_balancer():
        """Manage load balancers."""
        console.print("[yellow]Load balancer commands coming soon![/yellow]")

    @cli.group()
    def databases():
        """Manage managed databases."""
        console.print("[yellow]Database commands coming soon![/yellow]")

    @cli.group()
    def object_storage():
        """Manage object storage."""
        console.print("[yellow]Object storage commands coming soon![/yellow]")

    @cli.group()
    def users():
        """Manage users."""
        console.print("[yellow]User management commands coming soon![/yellow]")


# Register all commands when module is imported
register_commands()


if __name__ == "__main__":
    cli()
