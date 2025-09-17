"""
Vultr Billing FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr billing and account information.
"""

from typing import Any

from fastmcp import FastMCP

from .billing_analyzer import BillingAnalyzer


def create_billing_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr billing management.

    Args:
        vultr_client: VultrDNSServer instance

    Returns:
        Configured FastMCP instance with billing management tools
    """
    mcp = FastMCP(name="vultr-billing")
    billing_analyzer = BillingAnalyzer(vultr_client)

    @mcp.tool()
    async def get_account_info() -> dict[str, Any]:
        """
        Get account information including billing details.

        Returns:
            Account information and billing details
        """
        return await vultr_client.get_account_info()

    @mcp.tool()
    async def get_current_balance() -> dict[str, Any]:
        """
        Get current account balance and payment information.

        Returns:
            Current balance, pending charges, and payment history
        """
        return await vultr_client.get_current_balance()

    @mcp.tool()
    async def list_billing_history(
        days: int | None = 30, per_page: int | None = 25
    ) -> dict[str, Any]:
        """
        List billing history for the specified number of days.

        Args:
            days: Number of days to include (default: 30)
            per_page: Number of items per page (default: 25)

        Returns:
            Billing history with transaction details
        """
        return await vultr_client.list_billing_history(
            date_range=days, per_page=per_page
        )

    @mcp.tool()
    async def list_invoices(per_page: int | None = 25) -> dict[str, Any]:
        """
        List all invoices.

        Args:
            per_page: Number of items per page (default: 25)

        Returns:
            List of invoices with pagination info
        """
        return await vultr_client.list_invoices(per_page=per_page)

    @mcp.tool()
    async def get_invoice(invoice_id: str) -> dict[str, Any]:
        """
        Get details of a specific invoice.

        Args:
            invoice_id: The invoice ID

        Returns:
            Invoice details including line items
        """
        return await vultr_client.get_invoice(invoice_id)

    @mcp.tool()
    async def list_invoice_items(
        invoice_id: str, per_page: int | None = 25
    ) -> dict[str, Any]:
        """
        List items in a specific invoice.

        Args:
            invoice_id: The invoice ID
            per_page: Number of items per page (default: 25)

        Returns:
            Invoice line items with details
        """
        return await vultr_client.list_invoice_items(invoice_id, per_page=per_page)

    @mcp.tool()
    async def get_monthly_usage_summary(year: int, month: int) -> dict[str, Any]:
        """
        Get monthly usage and cost summary.

        Args:
            year: Year (e.g., 2024)
            month: Month (1-12)

        Returns:
            Monthly usage summary with service breakdown
        """
        return await vultr_client.get_monthly_usage_summary(year, month)

    @mcp.tool()
    async def get_current_month_summary() -> dict[str, Any]:
        """
        Get current month usage and cost summary.

        Returns:
            Current month usage summary with service breakdown
        """
        from datetime import datetime

        now = datetime.now()
        return await vultr_client.get_monthly_usage_summary(now.year, now.month)

    @mcp.tool()
    async def get_last_month_summary() -> dict[str, Any]:
        """
        Get last month usage and cost summary.

        Returns:
            Last month usage summary with service breakdown
        """
        from datetime import datetime, timedelta

        last_month = datetime.now() - timedelta(days=30)
        return await vultr_client.get_monthly_usage_summary(
            last_month.year, last_month.month
        )

    @mcp.tool()
    async def analyze_spending_trends(months: int = 6) -> dict[str, Any]:
        """
        Analyze spending trends over the past months.

        Args:
            months: Number of months to analyze (default: 6)

        Returns:
            Spending analysis with trends and recommendations
        """
        return await billing_analyzer.analyze_spending_trends(months)

    @mcp.tool()
    async def get_cost_breakdown_by_service(days: int = 30) -> dict[str, Any]:
        """
        Get cost breakdown by service for the specified period.

        Args:
            days: Number of days to analyze (default: 30)

        Returns:
            Service-wise cost breakdown with percentages
        """
        return await billing_analyzer.get_cost_breakdown_by_service(days)

    @mcp.tool()
    async def get_payment_summary() -> dict[str, Any]:
        """
        Get payment summary and account status.

        Returns:
            Payment summary with account status
        """
        account_info = await vultr_client.get_account_info()
        balance_info = await vultr_client.get_current_balance()

        return {
            "account_status": "active"
            if account_info.get("balance", 0) >= 0
            else "attention_required",
            "current_balance": balance_info.get("balance", 0),
            "pending_charges": balance_info.get("pending_charges", 0),
            "last_payment": {
                "date": balance_info.get("last_payment_date"),
                "amount": balance_info.get("last_payment_amount"),
            },
            "account_email": account_info.get("email"),
            "account_name": account_info.get("name"),
            "billing_email": account_info.get("billing_email"),
        }

    return mcp
