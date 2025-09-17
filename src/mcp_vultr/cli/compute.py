"""
Compute commands for mcp-vultr CLI.

This module contains compute-related commands including operating systems,
plans, startup scripts, and bare metal servers.
"""

import sys

import click

from .utils import console, handle_api_key_error, run_async_command


@click.group()
@click.pass_context
def operating_systems(ctx: click.Context):
    """Manage operating systems."""
    pass


@operating_systems.command("list")
@click.option(
    "--filter",
    type=click.Choice(["all", "linux", "windows", "apps"]),
    default="all",
    help="Filter OS types",
)
@click.pass_context
def os_list(ctx: click.Context, filter: str):
    """List operating systems."""
    api_key = handle_api_key_error(ctx.obj.get("api_key"))

    async def _list_os():
        from ..server import VultrDNSServer

        server = VultrDNSServer(api_key)

        if filter == "all":
            operating_systems = await server.list_operating_systems()
        elif filter == "linux":
            all_os = await server.list_operating_systems()
            linux_keywords = [
                "ubuntu",
                "debian",
                "centos",
                "fedora",
                "arch",
                "rocky",
                "alma",
                "opensuse",
            ]
            operating_systems = []
            for os_item in all_os:
                name = os_item.get("name", "").lower()
                if any(keyword in name for keyword in linux_keywords):
                    operating_systems.append(os_item)
        elif filter == "windows":
            all_os = await server.list_operating_systems()
            operating_systems = [
                os_item
                for os_item in all_os
                if "windows" in os_item.get("name", "").lower()
            ]
        else:  # apps
            all_os = await server.list_operating_systems()
            operating_systems = [
                os_item
                for os_item in all_os
                if os_item.get("family", "").lower() == "application"
            ]

        if not operating_systems:
            console.print(f"[yellow]No {filter} operating systems found[/yellow]")
            return

        console.print(
            f"[bold blue]Found {len(operating_systems)} {filter} operating system(s):[/bold blue]"
        )
        for os_item in operating_systems:
            name = os_item.get("name", "N/A")
            family = os_item.get("family", "N/A")
            arch = os_item.get("arch", "N/A")
            console.print(f"  • {name} ({family}, {arch}) - ID: {os_item.get('id')}")

    run_async_command(_list_os)


@click.group()
@click.pass_context
def plans(ctx: click.Context):
    """Manage hosting plans."""
    pass


@plans.command("list")
@click.option("--type", "plan_type", help="Filter by plan type (e.g., vc2, vhf)")
@click.pass_context
def plans_list(ctx: click.Context, plan_type: str | None):
    """List hosting plans."""
    api_key = handle_api_key_error(ctx.obj.get("api_key"))

    # Show helpful suggestions when no type is specified
    if not plan_type:
        from .utils import show_helpful_suggestions

        console.print(
            "[yellow]💡 No plan type specified. Here are the available options:[/yellow]\n"
        )
        show_helpful_suggestions("plans_list_no_type")
        console.print("\n[dim]Proceeding to list all plans...[/dim]\n")

    async def _list_plans():
        from ..server import VultrDNSServer

        server = VultrDNSServer(api_key)
        plans_list = await server.list_plans(plan_type)

        if not plans_list:
            console.print("[yellow]No plans found[/yellow]")
            return

        console.print(
            f"[bold blue]Available Plans ({len(plans_list)} found):[/bold blue]"
        )
        for plan in plans_list:
            plan_id = plan.get("id", "N/A")
            vcpus = plan.get("vcpu_count", "N/A")
            ram = plan.get("ram", "N/A")
            disk = plan.get("disk", "N/A")
            price = plan.get("monthly_cost", "N/A")
            console.print(
                f"  • {plan_id}: {vcpus} vCPU, {ram}MB RAM, {disk}GB disk - ${price}/mo"
            )

    run_async_command(_list_plans)


@click.group()
@click.pass_context
def startup_scripts(ctx: click.Context):
    """Manage startup scripts."""
    pass


@startup_scripts.command("list")
@click.pass_context
def scripts_list(ctx: click.Context):
    """List startup scripts."""
    api_key = handle_api_key_error(ctx.obj.get("api_key"))

    async def _list_scripts():
        from ..server import VultrDNSServer

        server = VultrDNSServer(api_key)
        scripts = await server.list_startup_scripts()

        if not scripts:
            console.print("[yellow]No startup scripts found[/yellow]")
            return

        console.print(f"[bold blue]Startup Scripts ({len(scripts)} found):[/bold blue]")
        for script in scripts:
            script_id = script.get("id", "N/A")
            name = script.get("name", "N/A")
            script_type = script.get("type", "N/A")
            created = script.get("date_created", "N/A")
            console.print(
                f"  • [{script_id}] {name} ({script_type}) - Created: {created}"
            )

    run_async_command(_list_scripts)


@startup_scripts.command("create")
@click.argument("name")
@click.argument("script", type=click.File("r"))
@click.option("--type", "script_type", default="boot", help="Script type (boot/pxe)")
@click.pass_context
def scripts_create(ctx: click.Context, name: str, script: click.File, script_type: str):
    """Create a new startup script."""
    api_key = handle_api_key_error(ctx.obj.get("api_key"))

    async def _create_script():
        from ..server import VultrDNSServer

        server = VultrDNSServer(api_key)
        script_content = script.read()

        result = await server.create_startup_script(name, script_content, script_type)

        if "error" in result:
            console.print(f"[red]Error creating script: {result['error']}[/red]")
            sys.exit(1)

        script_id = result.get("id", "Unknown")
        console.print(f"[green]✅ Created startup script [{script_id}]: {name}[/green]")

    run_async_command(_create_script)


@startup_scripts.command("delete")
@click.argument("script_id")
@click.confirmation_option(prompt="Are you sure you want to delete this script?")
@click.pass_context
def scripts_delete(ctx: click.Context, script_id: str):
    """Delete a startup script."""
    api_key = handle_api_key_error(ctx.obj.get("api_key"))

    async def _delete_script():
        from ..server import VultrDNSServer

        server = VultrDNSServer(api_key)
        success = await server.delete_startup_script(script_id)

        if success:
            console.print(f"[green]✅ Deleted startup script {script_id}[/green]")
        else:
            console.print(f"[red]❌ Failed to delete script {script_id}[/red]")
            sys.exit(1)

    run_async_command(_delete_script)


@click.group()
@click.pass_context
def bare_metal(ctx: click.Context):
    """Manage bare metal servers."""
    pass


@bare_metal.command("list")
@click.option("--status", help="Filter by status")
@click.option("--region", help="Filter by region")
@click.pass_context
def bare_metal_list(ctx: click.Context, status: str | None, region: str | None):
    """List bare metal servers."""
    api_key = handle_api_key_error(ctx.obj.get("api_key"))

    async def _list_servers():
        from ..server import VultrDNSServer

        server = VultrDNSServer(api_key)

        servers = await server.list_bare_metal_servers()

        # Apply filters if specified
        if status:  # noqa: F823
            servers = [
                s for s in servers if s.get("status", "").lower() == status.lower()
            ]
        if region:  # noqa: F823
            servers = [
                s for s in servers if s.get("region", "").lower() == region.lower()
            ]

        if not servers:
            filter_desc = []
            if status:
                filter_desc.append(f"status={status}")
            if region:
                filter_desc.append(f"region={region}")
            filter_str = f" with {', '.join(filter_desc)}" if filter_desc else ""
            console.print(f"[yellow]No bare metal servers found{filter_str}[/yellow]")
            return

        console.print(
            f"[bold blue]Bare Metal Servers ({len(servers)} found):[/bold blue]"
        )
        for srv in servers:
            server_id = srv.get("id", "N/A")
            label = srv.get("label", "N/A")
            status = srv.get("status", "N/A")
            region = srv.get("region", "N/A")
            plan = srv.get("plan", "N/A")
            console.print(f"  • [{server_id}] {label} - {status} ({region}, {plan})")

    run_async_command(_list_servers)


@bare_metal.command("get")
@click.argument("server_id")
@click.pass_context
def bare_metal_get(ctx: click.Context, server_id: str):
    """Get detailed bare metal server information."""
    api_key = handle_api_key_error(ctx.obj.get("api_key"))

    async def _get_server():
        from ..server import VultrDNSServer

        server = VultrDNSServer(api_key)
        srv_info = await server.get_bare_metal_server(server_id)

        if "error" in srv_info:
            console.print(f"[red]Error: {srv_info['error']}[/red]")
            sys.exit(1)

        console.print(f"[bold blue]Bare Metal Server: {server_id}[/bold blue]")
        console.print(f"  Label: {srv_info.get('label', 'N/A')}")
        console.print(f"  Status: {srv_info.get('status', 'N/A')}")
        console.print(f"  Region: {srv_info.get('region', 'N/A')}")
        console.print(f"  Plan: {srv_info.get('plan', 'N/A')}")
        console.print(f"  OS: {srv_info.get('os', 'N/A')}")

        if srv_info.get("main_ip"):
            console.print(f"  Main IP: {srv_info.get('main_ip')}")
        if srv_info.get("date_created"):
            console.print(f"  Created: {srv_info.get('date_created')}")

    run_async_command(_get_server)
