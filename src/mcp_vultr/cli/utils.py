"""
Shared utilities for CLI commands.
"""

import asyncio
import sys
from collections.abc import Callable
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Initialize Rich console
console = Console()


def handle_api_key_error(api_key: str | None) -> str:
    """Check if API key is provided and handle errors."""
    if not api_key:
        console.print("[red]Error: VULTR_API_KEY is required[/red]")
        console.print(
            "[yellow]Set it as an environment variable or use --api-key option[/yellow]"
        )
        sys.exit(1)
    return api_key


def run_async_command(func: Callable, *args, **kwargs) -> Any:
    """Run an async function in a Click command context."""
    try:
        return asyncio.run(func(*args, **kwargs))
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def display_table(title: str, data: list[dict], columns: list[str]) -> None:
    """Display data in a formatted table."""
    if not data:
        console.print(f"[yellow]No {title.lower()} found[/yellow]")
        return

    table = Table(title=title)
    for col in columns:
        table.add_column(col.replace("_", " ").title())

    for item in data:
        row_data = []
        for col in columns:
            value = item.get(col, "N/A")
            if isinstance(value, list | dict):
                value = str(value)
            row_data.append(str(value))
        table.add_row(*row_data)

    console.print(table)


def display_info_panel(title: str, data: dict) -> None:
    """Display information in a formatted panel."""
    info_text = Text()
    for key, value in data.items():
        if isinstance(value, list | dict):
            value = str(value)
        info_text.append(f"{key.replace('_', ' ').title()}: ", style="bold blue")
        info_text.append(f"{value}\n")

    panel = Panel(info_text, title=title, border_style="blue")
    console.print(panel)


def confirm_action(message: str) -> bool:
    """Ask for user confirmation."""
    return click.confirm(message)


def show_helpful_suggestions(
    command_context: str, missing_params: list[str] = None
) -> None:
    """Show helpful suggestions when CLI commands are missing parameters."""
    from rich.panel import Panel
    from rich.text import Text

    suggestions = Text()

    if command_context == "plans_list_no_type":
        suggestions.append("💡 Available Plan Types:\n", style="bold blue")
        suggestions.append("  • vc2     - Regular Performance instances\n")
        suggestions.append("  • vhf     - High Frequency instances\n")
        suggestions.append("  • voc     - Optimized Cloud instances\n")
        suggestions.append("  • vbm     - Bare Metal instances\n")
        suggestions.append("  • vcg     - Cloud GPU instances\n\n")
        suggestions.append("Example: ", style="bold")
        suggestions.append("vultr-cli plans list --type vc2", style="green")

    elif command_context == "regions_common":
        suggestions.append("🌍 Popular Regions:\n", style="bold blue")
        suggestions.append("  • ewr     - New York (NJ)\n")
        suggestions.append("  • ord     - Chicago (IL)\n")
        suggestions.append("  • dfw     - Dallas (TX)\n")
        suggestions.append("  • lax     - Los Angeles (CA)\n")
        suggestions.append("  • sea     - Seattle (WA)\n")
        suggestions.append("  • ams     - Amsterdam\n")
        suggestions.append("  • lhr     - London\n")
        suggestions.append("  • nrt     - Tokyo\n\n")
        suggestions.append(
            "💡 Use 'vultr-cli regions list' to see all available regions"
        )

    elif command_context == "bare_metal_create_help":
        suggestions.append(
            "🔧 To create a bare metal instance, you'll need:\n\n", style="bold blue"
        )
        suggestions.append("Required Parameters:\n", style="bold")
        suggestions.append("  • plan      - Bare metal plan ID\n")
        suggestions.append("  • region    - Region ID\n")
        suggestions.append("  • os        - Operating system ID\n\n")
        suggestions.append("Helpful Commands:\n", style="bold")
        suggestions.append(
            "  • vultr-cli plans list --type vbm    # List bare metal plans\n",
            style="green",
        )
        suggestions.append(
            "  • vultr-cli regions list             # List regions\n", style="green"
        )
        suggestions.append(
            "  • vultr-cli operating-systems list   # List OS options\n", style="green"
        )

    if suggestions.plain:
        panel = Panel(suggestions, title="💡 Helpful Information", border_style="blue")
        console.print(panel)
