"""
Billing commands for mcp-vultr CLI.

This module contains all billing-related commands including account info,
history, invoices, and spending analysis.
"""

import datetime

import click

from .utils import console, handle_api_key_error, run_async_command


@click.group()
@click.pass_context
def billing(ctx: click.Context):
    """Manage billing and account information."""
    pass


@billing.command("account")
@click.pass_context
def billing_account(ctx: click.Context):
    """Show account information and current balance."""
    api_key = handle_api_key_error(ctx.obj.get("api_key"))

    async def _show_account():
        from ..server import VultrDNSServer

        server = VultrDNSServer(api_key)
        account = await server.get_account_info()
        balance = await server.get_current_balance()

        console.print("[bold blue]Account Information:[/bold blue]")
        console.print(f"  Name: {account.get('name', 'N/A')}")
        console.print(f"  Email: {account.get('email', 'N/A')}")
        console.print(f"  Current Balance: ${balance.get('balance', 0):.2f}")
        console.print(f"  Pending Charges: ${balance.get('pending_charges', 0):.2f}")

        if balance.get("last_payment_date"):
            console.print(
                f"  Last Payment: ${balance.get('last_payment_amount', 0):.2f} on {balance.get('last_payment_date')}"
            )

    run_async_command(_show_account)


@billing.command("history")
@click.option("--days", type=int, default=30, help="Number of days to include")
@click.option("--limit", type=int, default=25, help="Number of items to show")
@click.pass_context
def billing_history(ctx: click.Context, days, limit):
    """Show billing history."""
    api_key = handle_api_key_error(ctx.obj.get("api_key"))

    async def _show_history():
        from ..server import VultrDNSServer

        server = VultrDNSServer(api_key)
        history = await server.list_billing_history(date_range=days, per_page=limit)
        billing_items = history.get("billing_history", [])

        if not billing_items:
            console.print(
                f"[yellow]No billing history found for the last {days} days[/yellow]"
            )
            return

        console.print(f"[bold blue]Billing History (last {days} days):[/bold blue]")
        total_cost = 0

        for item in billing_items:
            date = item.get("date", "Unknown")
            amount = float(item.get("amount", 0))
            description = item.get("description", "N/A")
            total_cost += amount

            console.print(f"  {date}: ${amount:.2f} - {description}")

        console.print(f"\n[bold]Total for period: ${total_cost:.2f}[/bold]")

    run_async_command(_show_history)


@billing.command("invoices")
@click.option("--limit", type=int, default=10, help="Number of invoices to show")
@click.pass_context
def billing_invoices(ctx: click.Context, limit):
    """List invoices."""
    api_key = handle_api_key_error(ctx.obj.get("api_key"))

    async def _list_invoices():
        from ..server import VultrDNSServer

        server = VultrDNSServer(api_key)
        invoices_data = await server.list_invoices(per_page=limit)
        invoices = invoices_data.get("billing_invoices", [])

        if not invoices:
            console.print("[yellow]No invoices found[/yellow]")
            return

        console.print("[bold blue]Recent Invoices:[/bold blue]")
        for invoice in invoices:
            invoice_id = invoice.get("id", "N/A")
            date = invoice.get("date", "Unknown")
            amount = invoice.get("amount", "N/A")
            status = invoice.get("status", "Unknown")

            console.print(f"  {invoice_id}: ${amount} - {date} ({status})")

    run_async_command(_list_invoices)


@billing.command("monthly")
@click.option("--year", type=int, help="Year (e.g., 2024)")
@click.option("--month", type=int, help="Month (1-12)")
@click.pass_context
def billing_monthly(ctx: click.Context, year, month):
    """Show monthly usage summary."""
    api_key = handle_api_key_error(ctx.obj.get("api_key"))

    # Default to current month if not specified
    if not year or not month:
        now = datetime.datetime.now()
        year = year or now.year
        month = month or now.month

    async def _show_monthly():
        from ..server import VultrDNSServer

        server = VultrDNSServer(api_key)
        summary = await server.get_monthly_usage_summary(year, month)

        console.print(f"[bold blue]Monthly Summary for {month}/{year}:[/bold blue]")
        console.print(f"  Total Cost: ${summary.get('total_cost', 0):.2f}")
        console.print(f"  Transactions: {summary.get('transaction_count', 0)}")
        console.print(
            f"  Average Daily Cost: ${summary.get('average_daily_cost', 0):.2f}"
        )

        services = summary.get("service_breakdown", {})
        if services:
            console.print("\n  Service Breakdown:")
            for service, cost in services.items():
                console.print(f"    {service}: ${cost:.2f}")

    run_async_command(_show_monthly)


@billing.command("trends")
@click.option("--months", type=int, default=6, help="Number of months to analyze")
@click.pass_context
def billing_trends(ctx: click.Context, months):
    """Analyze spending trends."""
    api_key = handle_api_key_error(ctx.obj.get("api_key"))

    async def _analyze_trends():
        from ..billing import create_billing_mcp
        from ..server import VultrDNSServer

        server = VultrDNSServer(api_key)
        create_billing_mcp(server)

        current_date = datetime.datetime.now()
        current_year = current_date.year
        current_month = current_date.month

        console.print(
            f"[bold blue]Spending Trends Analysis ({months} months):[/bold blue]"
        )

        # Calculate trends across the requested number of months
        monthly_data = []
        total_cost = 0

        for i in range(months):
            # Calculate the month/year for each period going backwards
            month = current_month - i
            year = current_year

            if month <= 0:
                month += 12
                year -= 1

            try:
                summary = await server.get_monthly_usage_summary(year, month)
                cost = float(summary.get("total_cost", 0))
                monthly_data.append(
                    {
                        "year": year,
                        "month": month,
                        "cost": cost,
                        "date": f"{year}-{month:02d}",
                    }
                )
                total_cost += cost
            except Exception as e:
                # Handle cases where data might not be available
                monthly_data.append(
                    {
                        "year": year,
                        "month": month,
                        "cost": 0,
                        "date": f"{year}-{month:02d}",
                        "error": str(e),
                    }
                )

        # Display trend analysis
        if len(monthly_data) >= 2:
            # Calculate month-over-month change
            current_cost = monthly_data[0]["cost"]
            previous_cost = monthly_data[1]["cost"]

            if previous_cost > 0:
                change_percent = ((current_cost - previous_cost) / previous_cost) * 100
                change_direction = (
                    "↑" if change_percent > 0 else "↓" if change_percent < 0 else "→"
                )
                console.print(
                    f"  Month-over-month change: {change_direction} {change_percent:+.1f}%"
                )

            # Show average monthly cost
            avg_cost = total_cost / len(monthly_data)
            console.print(f"  Average monthly cost: ${avg_cost:.2f}")

            # Show monthly breakdown
            console.print("  Monthly breakdown:")
            for data in reversed(monthly_data):  # Show chronologically
                if "error" not in data:
                    console.print(f"    {data['date']}: ${data['cost']:.2f}")
                else:
                    console.print(f"    {data['date']}: No data available")
        else:
            console.print(f"  Current month estimate: ${monthly_data[0]['cost']:.2f}")

        console.print(
            f"  [bold]Total cost over {months} months: ${total_cost:.2f}[/bold]"
        )

    run_async_command(_analyze_trends)
